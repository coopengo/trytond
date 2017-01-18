# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import threading
import json
from urlparse import urlparse
import logging
import redis
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.config import config

logger = logging.getLogger(__name__)
broker = None
listener = None


class Listener(threading.Thread):
    def __init__(self, r, channels):
        threading.Thread.__init__(self)
        self.channels = channels
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels.keys())
        self.started = False

    def run(self):
        self.started = True
        for item in self.pubsub.listen():
            channel = item['channel']
            data = item['data']
            fn = self.channels.get(channel, None)
            if fn and type(data) not in (int, long):
                fn(data)
        self.started = False

    def stop(self):
        self.pubsub.unsubscribe()


def init_pool_cb(data):
    data = json.loads(data)
    pid = data['pid']
    dbname = data['dbname']
    mypid = os.getpid()
    logger.info('init_pool(%s): %s <= %s', dbname, mypid, pid)
    if pid != mypid:
        Pool.stop(dbname)
        Pool(dbname).init()


def broadcast_init_pool():
    if is_started():
        pid = os.getpid()
        dbname = Transaction().database.name
        broker.publish('init_pool', json.dumps({'pid': pid, 'dbname': dbname}))
        logger.info('init pool(%s): %s =>>>', dbname, pid)


def is_started():
    global listener
    return listener is not None and listener.started


def start():
    if os.environ.get('WSGI_LOG_FILE'):
        global broker
        global listener
        logger.info('init_pool: start on %s', os.getpid())
        if broker:
            logger.warning('init_pool: already started on %s', os.getpid())
            return
        redis_url = config.get('cache', 'uri')
        if redis_url:
            url = urlparse(redis_url)
            assert url.scheme == 'redis', 'invalid redis url'
            host = url.hostname
            port = url.port
            db = url.path.strip('/')
            broker = redis.StrictRedis(host=host, port=port, db=db)
            listener = Listener(broker, {'init_pool': init_pool_cb})
            listener.start()


def stop():
    logger.info('init_pool: stop on %s', os.getpid())
    global listener
    if listener is not None:
        listener.stop()
    global broker
    if broker is not None:
        del broker
