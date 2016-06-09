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


class Listener(threading.Thread):
    def __init__(self, r, channels):
        threading.Thread.__init__(self)
        self.channels = channels
        self.redis = r
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channels.keys())

    def run(self):
        self.active = True
        for item in self.pubsub.listen():
            channel = item['channel']
            data = item['data']
            fn = self.channels.get(channel, None)
            if fn and type(data) not in (int, long):
                fn(data)
        self.active = False


def init_pool_cb(data):
    data = json.loads(data)
    pid = data['pid']
    dbname = data['dbname']
    logger.info('received init pool from %s for database %s', pid, dbname)
    if pid != os.getpid():
        Pool.stop(dbname)


def broadcast_init_pool():
    if is_active():
        pid = os.getpid()
        dbname = Transaction().database.name
        broker.publish('init_pool', json.dumps({'pid': pid, 'dbname': dbname}))
        logger.info('sent init pool for database %s', dbname)


redis_url = get_cache_redis()
if redis_url:
    url = urlparse(redis_url)
    assert url.scheme == 'redis', 'invalid redis url'
    host = url.hostname
    port = url.port
    db = url.path.strip('/')
    broker = redis.StrictRedis(host=host, port=port, db=db)

if broker:
    listener = Listener(broker, {'init_pool': init_pool_cb})
    listener.start()


def is_active():
    return listener is not None and listener.active
