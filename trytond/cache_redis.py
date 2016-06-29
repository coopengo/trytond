from threading import Lock
from urlparse import urlparse
import redis

from trytond.coog_config import get_cache_redis
from trytond.transaction import Transaction
from trytond.cache_utils import freeze

__all__ = ['Redis']


class Redis(object):
    _cache_instance = []
    _client = None
    _client_check_lock = Lock()

    @classmethod
    def ensure_client(cls):
        with cls._client_check_lock:
            if cls._client is None:
                redis_url = get_cache_redis()
                url = urlparse(redis_url)
                assert url.scheme == 'redis', 'invalid redis url'
                host = url.hostname
                port = url.port
                db = url.path.strip('/')
                cls._client = redis.StrictRedis(host=host, port=port, db=db)

    def __init__(self, name, size_limit=1024, context=True):
        self.context = context
        assert name not in set([i._name for i in self._cache_instance]), \
            '%s is already used' % name
        self._cache_instance.append(self)
        self._name = name
        self.ensure_client()

    def _namespace(self, dbname=None):
        if dbname is None:
            dbname = Transaction().database.name
        return '%s:%s' % (self._name, dbname)

    def _key(self, key):
        if self.context:
            t = Transaction()
            key = (key, t.user, freeze(t.context))
        return '%x' % hash(key)

    def get(self, key, default):
        namespace = self._namespace()
        key = self._key(key)
        result = self._client.hget(namespace, key)
        if result is None:
            return default
        else:
            return result

    def set(self, key, value):
        namespace = self._namespace()
        key = self._key(key)
        self._client.hset(namespace, key, value)

    def clear(self):
        namespace = self._namespace()
        self._client.delete(namespace)

    @classmethod
    def clean(cls, dbname):
        pass

    @classmethod
    def resets(cls, dbname):
        pass

    @classmethod
    def drop(cls, dbname):
        if cls._client is not None:
            for inst in cls._cache_instance:
                cls._client.delete(inst._namespace(dbname))
