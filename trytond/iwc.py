# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import threading
import json
from urlparse import urlparse
import logging
import redis
from trytond.pool import Pool
from trytond.config import config

logger = logging.getLogger(__name__)

no_redis = False
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


def get_worker_id():
    return '%s-%s' % (os.environ.get('HOSTNAME', 'localhost'), os.getpid())


def on_init_pool(data):
    data = json.loads(data)
    origin = data['origin']
    dbname = data['dbname']
    me = get_worker_id()
    if me != origin:
        logger.info('init_pool(%s): %s <= %s', dbname, me, origin)
        Pool.stop(dbname)
        Pool(dbname).init()


def broadcast_init_pool(dbname):
    global broker
    if broker is not None:
        me = get_worker_id()
        broker.publish('init_pool', json.dumps({
                    'origin': me,
                    'dbname': dbname
                    }))
        logger.info('init_pool(%s): %s =>>>', dbname, me)


def start():
    global no_redis, broker, listener
    if no_redis is True or listener is not None:
        return
    redis_url = config.get('cache', 'uri')
    if redis_url:
        logger.info('init_pool: %s starting', get_worker_id())
        url = urlparse(redis_url)
        assert url.scheme == 'redis', 'invalid redis url'
        host = url.hostname
        port = url.port
        db = url.path.strip('/')
        broker = redis.StrictRedis(host=host, port=port, db=db)
        listener = Listener(broker, {'init_pool': on_init_pool})
        listener.start()
    else:
        logger.info('init_pool: %s no redis config to start', get_worker_id())
        no_redis = True


def stop():
    global no_redis, broker, listener
    if no_redis is True or listener is None:
        return
    logger.info('init_pool: %s stopping', get_worker_id())
    listener.stop()
    del broker
