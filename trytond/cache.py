# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from threading import Lock
from collections import OrderedDict
import msgpack

from sql import Table
from sql.functions import CurrentTimestamp

from trytond.coog_config import get_cache_redis
from trytond.transaction import Transaction
from trytond.cache_utils import freeze, encode_hook, decode_hook, Default
try:
    from trytond.cache_redis import Redis
except ImportError:
    logging.warning('Could not import Redis packages for cache')
    Redis = None


__all__ = ['_Cache', 'Cache', 'LRUDict']


class _Cache(object):
    """
    A key value LRU cache with size limit.
    """
    _cache_instance = []
    _resets = {}
    _resets_lock = Lock()

    def __init__(self, name, size_limit=1024, context=True):
        self.size_limit = size_limit
        self.context = context
        self._cache = {}
        assert name not in set([i._name for i in self._cache_instance]), \
            '%s is already used' % name
        self._cache_instance.append(self)
        self._name = name
        self._timestamp = None
        self._lock = Lock()

    def _key(self, key):
        if self.context:
            return (key, Transaction().user, freeze(Transaction().context))
        return key

    def get(self, key, default):
        dbname = Transaction().database.name
        key = self._key(key)
        with self._lock:
            cache = self._cache.setdefault(dbname, LRUDict(self.size_limit))
            try:
                result = cache[key] = cache.pop(key)
                return result
            except KeyError:
                # JCA : Properly crash on type error
                return default

    def set(self, key, value):
        dbname = Transaction().database.name
        key = self._key(key)
        with self._lock:
            cache = self._cache.setdefault(dbname, LRUDict(self.size_limit))
            try:
                cache[key] = value
            except TypeError:
                # JCA : Properly detect non hashable keys
                raise
        return value

    def _empty(self, dbname):
        self._cache[dbname] = LRUDict(self.size_limit)

    def clear(self):
        dbname = Transaction().database.name
        with self._resets_lock:
            self._resets.setdefault(dbname, set())
            self._resets[dbname].add(self._name)
        with self._lock:
            self._empty(dbname)

    @classmethod
    def clean(cls, dbname):
        # bypass cache sync mechanism (no need on redis, no effect on test)
        # fix on master: no patch on cache + memoize for ir/ui/view.py
        return
        with Transaction().new_transaction() as transaction,\
                transaction.connection.cursor() as cursor:
            table = Table('ir_cache')
            cursor.execute(*table.select(table.timestamp, table.name))
            timestamps = {}
            for timestamp, name in cursor.fetchall():
                timestamps[name] = timestamp
        for inst in cls._cache_instance:
            if inst._name in timestamps:
                with inst._lock:
                    if (not inst._timestamp
                            or timestamps[inst._name] > inst._timestamp):
                        inst._timestamp = timestamps[inst._name]
                        inst._empty(dbname)

    @classmethod
    def resets(cls, dbname):
        # bypass cache sync mechanism (no need on redis, no effect on test)
        # fix on master: no patch on cache + memoize for ir/ui/view.py
        return
        table = Table('ir_cache')
        with Transaction().new_transaction() as transaction,\
                transaction.connection.cursor() as cursor,\
                cls._resets_lock:
            cls._resets.setdefault(dbname, set())
            for name in cls._resets[dbname]:
                cursor.execute(*table.select(table.name,
                        where=table.name == name))
                if cursor.fetchone():
                    # It would be better to insert only
                    cursor.execute(*table.update([table.timestamp],
                            [CurrentTimestamp()],
                            where=table.name == name))
                else:
                    cursor.execute(*table.insert(
                            [table.timestamp, table.name],
                            [[CurrentTimestamp(), name]]))
            cls._resets[dbname].clear()

    @classmethod
    def drop(cls, dbname):
        for inst in cls._cache_instance:
            inst._cache.pop(dbname, None)


class Cache(object):
    # AKE: this class wraps technical holders and manage serialization
    def __init__(self, *args, **kwargs):
        redis = get_cache_redis()
        if redis is None:
            self.cache = _Cache(*args, **kwargs)
        else:
            assert Redis is not None, 'Packages needed by Redis are missing'
            self.cache = Redis(*args, **kwargs)

    def get(self, key, default=None):
        result = self.cache.get(key, Default)
        if result is Default:
            return default
        else:
            return msgpack.unpackb(result, encoding='utf-8',
                object_hook=decode_hook)

    def set(self, key, value):
        value = msgpack.packb(value, use_bin_type=True, default=encode_hook)
        self.cache.set(key, value)

    def clear(self):
        self.cache.clear()

    @staticmethod
    def clean(dbname):
        _Cache.clean(dbname)
        if Redis is not None:
            Redis.clean(dbname)

    @staticmethod
    def resets(dbname):
        _Cache.resets(dbname)
        if Redis is not None:
            Redis.resets(dbname)

    @staticmethod
    def drop(dbname):
        _Cache.drop(dbname)
        if Redis is not None:
            Redis.drop(dbname)


class LRUDict(OrderedDict):
    """
    Dictionary with a size limit.
    If size limit is reached, it will remove the first added items.
    """
    __slots__ = ('size_limit',)

    def __init__(self, size_limit, *args, **kwargs):
        assert size_limit > 0
        self.size_limit = size_limit
        super(LRUDict, self).__init__(*args, **kwargs)
        self._check_size_limit()

    def __setitem__(self, key, value):
        super(LRUDict, self).__setitem__(key, value)
        self._check_size_limit()

    def update(self, *args, **kwargs):
        super(LRUDict, self).update(*args, **kwargs)
        self._check_size_limit()

    def setdefault(self, key, default=None):
        default = super(LRUDict, self).setdefault(key, default=default)
        self._check_size_limit()
        return default

    def _check_size_limit(self):
        while len(self) > self.size_limit:
            self.popitem(last=False)


class LRUDictTransaction(LRUDict):
    """
    Dictionary with a size limit. (see LRUDict)
    It is refreshed when transaction counter is changed.
    """
    __slots__ = ('transaction', 'counter')

    def __init__(self, *args, **kwargs):
        super(LRUDictTransaction, self).__init__(*args, **kwargs)
        self.transaction = Transaction()
        self.counter = self.transaction.counter

    def clear(self):
        super(LRUDictTransaction, self).clear()
        self.counter = self.transaction.counter

    def refresh(self):
        if self.counter != self.transaction.counter:
            self.clear()
