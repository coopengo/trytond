import time
from threading import Lock
import redis
from urlparse import urlparse

from trytond.config import config

_client = None
_client_lock = Lock()


def get_client():
    global _client, _client_lock
    with _client_lock:
        if _client is None:
            redis_uri = config.get('cache', 'uri')
            assert redis_uri, 'redis uri not set'
            url = urlparse(redis_uri)
            assert url.scheme == 'redis', 'invalid redis url'
            host = url.hostname
            port = url.port
            db = url.path.strip('/')
            _client = redis.StrictRedis(host=host, port=port, db=db)
    return _client


def key(dbname, user, session):
    return 'session:%s:%d:%s' % (dbname, user, session)


def has_session(dbname, user, session):
    last = get_client().get(key(dbname, user, session))
    if not last:
        return False
    last = int(last)
    now = int(time.time())
    timeout = config.getint('session', 'timeout')
    if (now - last > timeout):
        del_session(dbname, user, session)
        return False
    else:
        return True


def set_session(dbname, user, session):
    get_client().set(key(dbname, user, session), int(time.time()))


def del_session(dbname, user, session):
    get_client().delete(key(dbname, user, session))
