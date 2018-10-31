# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from threading import local
from sql import Flavor

from trytond import backend
from trytond.config import config

logger = logging.getLogger(__name__)


class _AttributeManager(object):
    '''
    Manage Attribute of transaction
    '''

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return Transaction()

    def __exit__(self, type, value, traceback):
        for name, value in self.kwargs.items():
            setattr(Transaction(), name, value)


class _Local(local):

    def __init__(self):
        # Transaction stack control
        self.transactions = []
        self.tasks = []


class Transaction(object):
    '''
    Control the transaction
    '''

    _local = _Local()

    cache_keys = {'language', 'fuzzy_translation', '_datetime',
        '_datetime_exclude'}

    database = None
    readonly = False
    connection = None
    close = None
    user = None
    context = None
    create_records = None
    delete_records = None
    delete = None  # TODO check to merge with delete_records
    timestamp = None

    def __new__(cls, new=False):
        transactions = cls._local.transactions
        if new or not transactions:
            instance = super(Transaction, cls).__new__(cls)
            instance.cache = {}
            instance._atexit = []
            transactions.append(instance)
        else:
            instance = transactions[-1]
        return instance

    @property
    def tasks(self):
        return self._local.tasks

    def get_cache(self):
        from trytond.cache import LRUDict
        keys = tuple(((key, self.context[key])
                for key in sorted(self.cache_keys)
                if key in self.context))
        return self.cache.setdefault((self.user, keys),
            LRUDict(config.getint('cache', 'model')))

    def start(self, database_name, user, readonly=False, context=None,
            close=False, autocommit=False, _nocache=False):
        '''
        Start transaction
        '''
        Database = backend.get('Database')
        assert self.user is None
        assert self.database is None
        assert self.close is None
        assert self.context is None
        if not database_name:
            database = Database().connect()
        else:
            database = Database(database_name).connect()
        Flavor.set(Database.flavor)
        self.connection = database.get_connection(readonly=readonly,
            autocommit=autocommit)
        self.user = user
        self.database = database
        self.readonly = readonly
        self.close = close
        self.context = context or {}
        self.create_records = {}
        self.delete_records = {}
        self.delete = {}
        self.timestamp = {}
        self.counter = 0
        self._datamanagers = []
        self._sub_transactions = []
        self._nocache = _nocache
        if not _nocache:
            from trytond.cache import Cache
            try:
                Cache.clean(database.name)
            except BaseException:
                self.stop(False)
                raise
        return self

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.stop(type is None)

    def stop(self, commit=False):
        transactions = self._local.transactions
        try:
            if transactions.count(self) == 1:
                try:
                    try:
                        # Transaction must be commited to send notifications
                        if commit and (not self.readonly
                                or self.database.has_channel()):
                            self.commit()
                        else:
                            self.rollback()
                    finally:
                        self.database.put_connection(
                            self.connection, self.close)
                finally:
                    self.database = None
                    self.readonly = False
                    self.connection = None
                    self.close = None
                    self.user = None
                    self.context = None
                    self.create_records = None
                    self.delete_records = None
                    self.delete = None
                    self.timestamp = None
                    self._datamanagers = []

                for func, args, kwargs in self._atexit:
                    func(*args, **kwargs)
        finally:
            current_instance = transactions.pop()
        assert current_instance is self, transactions

    def set_context(self, context=None, **kwargs):
        if context is None:
            context = {}
        manager = _AttributeManager(context=self.context)
        self.context = self.context.copy()
        self.context.update(context)
        if kwargs:
            self.context.update(kwargs)
        return manager

    def reset_context(self):
        manager = _AttributeManager(context=self.context)
        self.context = {}
        return manager

    def set_user(self, user, set_context=False):
        if user != 0 and set_context:
            raise ValueError('set_context only allowed for root')
        manager = _AttributeManager(user=self.user,
                context=self.context)
        self.context = self.context.copy()
        if set_context:
            if user != self.user:
                self.context['user'] = self.user
        else:
            self.context.pop('user', None)
        self.user = user
        return manager

    def set_current_transaction(self, transaction):
        self._local.transactions.append(transaction)
        return transaction

    def new_transaction(self, autocommit=False, readonly=False,
            _nocache=False):
        transaction = Transaction(new=True)
        return transaction.start(self.database.name, self.user,
            context=self.context, close=self.close, readonly=readonly,
            autocommit=autocommit, _nocache=_nocache)

    def add_sub_transactions(self, sub_transactions):
        self._sub_transactions.extend(sub_transactions)

    def commit(self):
        try:
            if self._datamanagers:
                for datamanager in self._datamanagers:
                    datamanager.tpc_begin(self)
                for datamanager in self._datamanagers:
                    datamanager.commit(self)
                for datamanager in self._datamanagers:
                    datamanager.tpc_vote(self)
            # ABD: Some datamanager may returns transactions which should
            # be committed just before the main transaction
            for sub_transaction in self._sub_transactions:
                # Does not handle TPC or recursive transaction commit
                # This just commits the sub transactions to avoid any crashes
                # which could occur otherwise.
                sub_transaction.connection.commit()
            self.connection.commit()
        except:
            self.rollback()
            raise
        else:
            try:
                for datamanager in self._datamanagers:
                    datamanager.tpc_finish(self)
            except:
                logger.critical('A datamanager raised an exception in'
                    ' tpc_finish, the data might be inconsistant',
                    exc_info=True)
        if not self._nocache:
            from trytond.cache import Cache
            Cache.resets(self.database.name)

    def rollback(self):
        for sub_transaction in self._sub_transactions:
            sub_transaction.rollback()
        for cache in self.cache.values():
            cache.clear()
        for datamanager in self._datamanagers:
            datamanager.tpc_abort(self)
        self.connection.rollback()
        if not self._nocache:
            from trytond.cache import Cache
            Cache.resets(self.database.name)

    def join(self, datamanager):
        try:
            idx = self._datamanagers.index(datamanager)
            return self._datamanagers[idx]
        except ValueError:
            self._datamanagers.append(datamanager)
            return datamanager

    def atexit(self, func, *args, **kwargs):
        self._atexit.append((func, args, kwargs))

    @property
    def language(self):
        def get_language():
            from trytond.pool import Pool
            Config = Pool().get('ir.configuration')
            return Config.get_language()
        if self.context:
            return self.context.get('language') or get_language()
        return get_language()
