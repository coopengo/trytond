import os
import threading
import json
from urlparse import urlparse
import logging
import redis
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.coog_config import get_cache_redis

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
    logger.info('received init pool from %s for database %s', pid, dbname)
    if pid != os.getpid():
        Pool.stop(dbname)


def broadcast_init_pool():
    if is_started():
        pid = os.getpid()
        dbname = Transaction().database.name
        broker.publish('init_pool', json.dumps({'pid': pid, 'dbname': dbname}))
        logger.info('sent init pool for database %s', dbname)


def is_started():
    global listener
    return listener is not None and listener.started


def start():
    logger.info('starting worker listener')
    redis_url = get_cache_redis()
    global broker
    global listener
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
    logger.info('stopping worker listener')
    global listener
    if listener is not None:
        listener.stop()
    global broker
    if broker is not None:
        del broker
