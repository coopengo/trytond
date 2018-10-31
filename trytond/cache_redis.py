# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from threading import Lock
from urllib.parse import urlparse
import redis

from trytond.config import config
from trytond.transaction import Transaction
from trytond.cache import BaseCache
from trytond.cache_serializer import pack, unpack


class RedisCache(BaseCache):
    _client = None
    _client_check_lock = Lock()
    #PKUNK 9502 Redis ttl
    _ttl = config.getint('cache', 'redis_ttl') or 60 * 60 * 12

    @classmethod
    def ensure_client(cls):
        with cls._client_check_lock:
            if cls._client is None:
                redis_uri = config.get('cache', 'uri')
                assert redis_uri, 'redis uri not set'
                url = urlparse(redis_uri)
                assert url.scheme == 'redis', 'invalid redis url'
                host = url.hostname
                port = url.port
                db = url.path.strip('/')
                cls._client = redis.StrictRedis(host=host, port=port, db=db)

    def __init__(self, name, size_limit=1024, context=True):
        super(RedisCache, self).__init__(name, size_limit, context)
        self.ensure_client()

    def _namespace(self, dbname=None):
        if dbname is None:
            dbname = Transaction().database.name
        return '%s:%s' % (dbname, self._name)

    def _key(self, key):
        k = super(RedisCache, self)._key(key)
        return '%x' % hash(k)

    def get(self, key, default=None):
        namespace = self._namespace()
        key = self._key(key)
        #PKUNK 9502 normal get 
        result = self._client.get('%s:%s' % (namespace, key))
        if result is None:
            return default
        else:
            return unpack(result)

    #PKUNK 9502 add ttl on set
    def set(self, key, value, ttl=None):
        if ttl:
            assert isinstance(ttl, int)
        namespace = self._namespace()
        key = self._key(key)
        value = pack(value)
        #PKUNK 9502 change method hset to setex
        self._client.setex(name='%s:%s' % (namespace, key), value=value, time=ttl or self._ttl)

    def clear(self):
        namespace = self._namespace()
        #PKUNK 9502 Add loop to clean all key
        for key in self._client.scan_iter(match='%s:*' % (namespace)):
            self._client.delete(key)

    @staticmethod
    def clean(dbname):
        pass

    @staticmethod
    def resets(dbname):
        pass

    @classmethod
    def drop(cls, dbname):
        for inst in cls._cache_instance:
            cls._client.delete(inst._namespace(dbname))
