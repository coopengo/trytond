# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import datetime
from decimal import Decimal
from threading import Lock
from urlparse import urlparse
import redis
import msgpack

from trytond.config import config
from trytond.transaction import Transaction
from trytond.cache import BaseCache


def encode_hook(o):
    if isinstance(o, Decimal):
        return {
            '__decimal__': True,
            'data': str(o)
        }
    if isinstance(o, datetime.datetime):
        return {
            '__datetime__': True,
            'data': (o.year, o.month, o.day, o.hour, o.minute, o.second,
                o.microsecond)
        }
    if isinstance(o, datetime.date):
        return {
            '__date__': True,
            'data': (o.year, o.month, o.day)
        }
    if isinstance(o, datetime.time):
        return {
            '__time__': True,
            'data': (o.hour, o.minute, o.second, o.microsecond)
        }
    if isinstance(o, datetime.timedelta):
        return {
            '__timedelta__': True,
            'data': o.total_seconds()
        }
    if isinstance(o, set):
        return {
            '__set__': True,
            'data': tuple(o)
        }
    return o


def decode_hook(o):
    if '__decimal__' in o:
        return Decimal(o['data'])
    elif '__datetime__' in o:
        return datetime.datetime(*o['data'])
    elif '__date__' in o:
        return datetime.date(*o['data'])
    elif '__time__' in o:
        return datetime.time(*o['data'])
    elif '__timedelta__' in o:
        return datetime.timedelta(o['data'])
    elif '__set__' in o:
        return set(o['data'])
    return o


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
            return msgpack.unpackb(result, encoding='utf-8',
                object_hook=decode_hook)

    def set(self, key, value):
        namespace = self._namespace()
        key = self._key(key)
        value = msgpack.packb(value, use_bin_type=True, default=encode_hook)
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
