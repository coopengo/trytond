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


def has_session(user, session):
    last = get_client().get('session:%d:%s' % (user, session))
    if not last:
        return False
    last = int(last)
    now = int(time.time())
    timeout = config.getint('session', 'timeout')
    if (now - last > timeout):
        del_session(user, session)
        return False
    else:
        return True


def set_session(user, session):
    get_client().set('session:%d:%s' % (user, session), int(time.time()))


def del_session(user, session):
    get_client().delete('session:%d:%s' % (user, session))
