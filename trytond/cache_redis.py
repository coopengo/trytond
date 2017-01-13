# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from threading import Lock
from urlparse import urlparse
import redis

from trytond.config import config
from trytond.transaction import Transaction
from trytond.cache import BaseCache
from trytond.cache_serializer import pack, unpack


class RedisCache(BaseCache):
    _client = None
    _client_check_lock = Lock()

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
        result = self._client.hget(namespace, key)
        if result is None:
            return default
        else:
            return unpack(result)

    def set(self, key, value):
        namespace = self._namespace()
        key = self._key(key)
        value = pack(value)
        self._client.hset(namespace, key, value)

    def clear(self):
        namespace = self._namespace()
        self._client.delete(namespace)

    def drop_inst(self, dbname):
        namespace = self._namespace()
        self._client.delete(namespace)

    @classmethod
    def clean_inst(self, dbname, timestamps):
        pass

    @classmethod
    def resets_cls(cls, dbname, cursor, table):
        pass
