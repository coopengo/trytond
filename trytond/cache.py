# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from threading import Lock
from collections import OrderedDict

from sql import Table
from sql.functions import CurrentTimestamp

from trytond.config import config
from trytond.transaction import Transaction
from trytond.cache_serializer import pack, unpack
from trytond.tools import resolve

__all__ = ['BaseCache', 'Cache', 'LRUDict']


def freeze(o):
    if isinstance(o, (set, tuple, list)):
        return tuple(freeze(x) for x in o)
    elif isinstance(o, dict):
        return frozenset((x, freeze(y)) for x, y in o.iteritems())
    else:
        return o


class BaseCache(object):
    _cache_instance = []

    def __init__(self, name, size_limit=1024, context=True):
        assert name not in set([i._name for i in self._cache_instance]), \
            '%s is already used' % name
        self._name = name
        self.size_limit = size_limit
        self.context = context
        self._cache_instance.append(self)

    def _key(self, key):
        if self.context:
            return (key, Transaction().user, freeze(Transaction().context))
        return key

    def get(self, key, default=None):
        raise NotImplemented

    def set(self, key, value):
        raise NotImplemented

    def clear(self):
        raise NotImplemented

    def drop_inst(self, dbname):
        raise NotImplemented

    @staticmethod
    def drop(dbname):
        for inst in BaseCache._cache_instance:
            inst.drop_inst(dbname)

    def clean_inst(self, dbname, timestamps):
        raise NotImplemented

    @staticmethod
    def clean(dbname):
        with Transaction().new_transaction(_nocache=True) as transaction,\
                transaction.connection.cursor() as cursor:
            table = Table('ir_cache')
            cursor.execute(*table.select(table.timestamp, table.name))
            timestamps = {}
            for timestamp, name in cursor.fetchall():
                timestamps[name] = timestamp
        for inst in BaseCache._cache_instance:
            inst.clean_inst(dbname, timestamps)

    @classmethod
    def resets_cls(cls, dbname, cursor, table):
        raise NotImplemented

    @staticmethod
    def resets(dbname):
        table = Table('ir_cache')
        with Transaction().new_transaction(_nocache=True) as transaction,\
                transaction.connection.cursor() as cursor:
            klasses = [i.__class__ for i in BaseCache._cache_instance]
            klasses = list(set(klasses))
            for klass in klasses:
                klass.resets_cls(dbname, cursor, table)


class MemoryCache(BaseCache):
    """
    A key value LRU cache with size limit.
    """
    _resets = {}
    _resets_lock = Lock()

    def __init__(self, name, size_limit=1024, context=True):
        super(MemoryCache, self).__init__(name, size_limit, context)
        self._cache = {}
        self._timestamp = None
        self._lock = Lock()

    def get(self, key, default=None):
        dbname = Transaction().database.name
        key = self._key(key)
        with self._lock:
            cache = self._cache.setdefault(dbname, LRUDict(self.size_limit))
            try:
                result = cache[key] = cache.pop(key)
                return result
            # JCA: Properly crash on type error
            except KeyError:
                return default

    def set(self, key, value):
        dbname = Transaction().database.name
        key = self._key(key)
        with self._lock:
            cache = self._cache.setdefault(dbname, LRUDict(self.size_limit))
            # JCA: Properly crash on type error
            cache[key] = value
        return value

    def clear(self):
        dbname = Transaction().database.name
        with self._resets_lock:
            self._resets.setdefault(dbname, set())
            self._resets[dbname].add(self._name)
        with self._lock:
            self._cache[dbname] = LRUDict(self.size_limit)

    def drop_inst(self, dbname):
        with self._lock:
            self._cache.pop(dbname, None)

    def clean_inst(self, dbname, timestamps):
        if self._name in timestamps:
            with self._lock:
                if (not self._timestamp
                        or timestamps[self._name] > self._timestamp):
                    self._timestamp = timestamps[self._name]
                    self._cache[dbname] = LRUDict(self.size_limit)

    @classmethod
    def resets_cls(cls, dbname, cursor, table):
        with cls._resets_lock:
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


class DefaultCacheValue:
    pass


_default_cache_value = DefaultCacheValue()


class SerializableMemoryCache(MemoryCache):
    def get(self, key, default=None):
        result = super(SerializableMemoryCache, self).get(key,
            _default_cache_value)
        return default if result == _default_cache_value else unpack(result)

    def set(self, key, value):
        super(SerializableMemoryCache, self).set(key, pack(value))


if config.get('cache', 'class'):
    Cache = resolve(config.get('cache', 'class'))
else:
    # JCA : Use serializable memory cache by default to avoid cache corruption
    Cache = SerializableMemoryCache


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
