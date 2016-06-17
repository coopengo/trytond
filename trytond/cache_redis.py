from threading import Lock
import msgpack
from decimal import Decimal
import datetime
from urlparse import urlparse
import redis

from trytond.coog_config import get_cache_redis
from trytond.transaction import Transaction

__all__ = ['Redis']


def freeze(o):
    if isinstance(o, (set, tuple, list)):
        return tuple(freeze(x) for x in o)
    elif isinstance(o, dict):
        return frozenset((x, freeze(y)) for x, y in o.iteritems())
    else:
        return o


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
