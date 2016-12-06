# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
##########################################
# ### Performance Analyzer for Trytond ###
##########################################
#
# - logs server calls
# - analyse calls (number of calls, server time, queried tables)
# - for specific methods profile call
# - for long db accesses: gets backtrace and sql query
#
# Analyse data
# - data is stored in redis (specific data types to analyse)
# - data format is documented below
# - a Lua script is provided to have some interesting reports
#
#########################################################
# ### Configuration block (to append to trytond.conf) ###
#########################################################
#
# [perf]
# broker = redis://127.0.0.1:6379/15  => redis url for storage
# users = admin                       => users with active analyzing
#
# profile = model.ir.ui.menu.read     => activate profiling
# db = model.ir.ui.menu.read          => db extra logs (table / act / tm)
#
# query = 1                           => log bt and sql for queries > x secs
#
############################
# ### Log storage format ###
############################
#
# s:<sess_id> => hash
#     - user   => session's user
#     - first  => first call datetime
#     - last   => last call datetime
#     - nb     => server calls during session
#     - tm     => server time during session
#
# m:n:<sess_id> => sorted set
#     - key   => method name
#     - score => server calls number to method during session
#
# m:t:<sess_id> => sorted set
#     - key   => method name
#     - score => server calls time for method during session
#
# t:n:<sess_id> => sorted set
#     - key   => table name
#     - score => table queries number during session
#
# t:t:<sess_id> => sorted set
#     - key   => table name
#     - score => table queries time during session
#
# c:<sess_id>:<call_rank> => hash
#     - method       => method name
#     - dt           => call datetime
#     - tm           => server time
#     - db_nb        => db select number
#     - db_tm        => db select server time
#
# x:p:<sess_id>:<call_rank> => server call profiling
#
# x:db:<sess_id>:<call_rank> => list
#     - msgpack (action, table, tm)
#
# q:<sess_id> => list
#     - msgpack (method, call, action, table, sql, bt)


import re
import time
import logging
import traceback
import pstats

try:
    import redis
    import msgpack
except ImportError:
    redis = None
    msgpack = None

from threading import local
from urlparse import urlparse
from datetime import datetime
import cStringIO as StringIO
import cProfile as Profile

from sql import Table
from trytond.transaction import Transaction
from trytond.config import config

logger = logging.getLogger(__name__)


def login_from_id(user_id):
    with Transaction().new_transaction(readonly=True) as t:
        cursor = t.connection.cursor()
        table = Table('res_user')
        cursor.execute(*table.select(table.login,
                where=table.id == user_id))
        return cursor.fetchone()[0]


def get_broker():
    return config.get('perf', 'broker', default=None)


def check_user(login):
    users = config.get('perf', 'users', default='')
    users = [u.strip() for u in users.split(',') if len(u) > 0]
    return login in users


def check_profile(method):
    methods = config.get('perf', 'profile', default='')
    methods = [m.strip() for m in methods.split(',') if len(m) > 0]
    return method in methods


def check_db(method):
    methods = config.get('perf', 'db', default='')
    methods = [m.strip() for m in methods.split(',') if len(m) > 0]
    return method in methods


def check_query(exec_time):
    limit = config.get('perf', 'query', default=None)
    return limit is not None and exec_time > float(limit)


class ThreadLog(local):
    inst = None


class ThreadSingleton(type):
    def __call__(cls, *args, **kwargs):
        if ThreadLog.inst is None:
            ThreadLog.inst = super(ThreadSingleton, cls).__call__(*args,
                **kwargs)
        return ThreadLog.inst


class PerfLog(object):
    __metaclass__ = ThreadSingleton

    def __init__(self):
        logger.debug('new instance')
        self.broker = None
        self.session = None
        self.method = None
        self.id = None
        broker_url = get_broker()
        if broker_url is not None:
            try:
                url = urlparse(broker_url)
                assert url.scheme == 'redis', 'invalid redis url'
                host = url.hostname
                port = url.port
                db = url.path.strip('/')
                assert redis, 'redis is not installed'
                assert msgpack, 'msgpack is not installed'
                self.broker = redis.StrictRedis(host=host, port=port, db=db)
            except:
                logger.exception('init failed')
                self.broker = None

    def is_active(self):
        return self.id is not None

    def _sess_key(self):
        return 's:%s' % self.session

    def _meth_n_key(self):
        return 'm:n:%s' % self.session

    def _meth_t_key(self):
        return 'm:t:%s' % self.session

    def _tab_n_key(self):
        return 't:n:%s' % self.session

    def _tab_t_key(self):
        return 't:t:%s' % self.session

    def _call_key(self):
        return 'c:%s:%s' % (self.session, self.id)

    def _x_key(self, *args):
        res = 'x'
        for item in args:
            res += ':%s' % item
        return '%s:%s:%s' % (res, self.session, self.id)

    def _q_key(self):
        return 'q:%s' % self.session

    def on_enter(self, user, session, method, args, kwargs):
        if self.broker is not None:
            login = login_from_id(user)
            if check_user(login):
                self.dt = time.time()
                dts = datetime.fromtimestamp(self.dt).strftime(
                    '%Y-%m-%d@%H:%M:%S.%f')
                # session
                self.session = session
                sess_key = self._sess_key()
                self.broker.hsetnx(sess_key, 'user', login)
                id = self.broker.hincrby(sess_key, 'nb', 1)
                self.broker.hsetnx(sess_key, 'first', dts)
                self.broker.hset(sess_key, 'last', dts)
                # method
                self.method = method
                # call
                self.id = id
                self.broker.hmset(self._call_key(), {'method': self.method,
                        'dt': dts})

    def on_leave(self, result):
        if self.is_active():
            tm = time.time() - self.dt
            # session
            self.broker.hincrbyfloat(self._sess_key(), 'tm', tm)
            # method
            self.broker.zincrby(self._meth_n_key(), self.method)
            self.broker.zincrby(self._meth_t_key(), self.method, tm)
            # call
            self.broker.hset(self._call_key(), 'tm', tm)
        ThreadLog.inst = None

    def set_profile(self, value):
        self.broker.set(self._x_key('p'), value)

    def log_db(self, action, table, tm):
        if table:
            self.broker.zincrby(self._tab_n_key(), table)
            self.broker.zincrby(self._tab_t_key(), table, tm)
        call_key = self._call_key()
        self.broker.hincrby(call_key, 'db_nb', 1)
        self.broker.hincrbyfloat(call_key, 'db_tm', tm)
        if check_db(self.method):
            self.broker.rpush(self._x_key('db'), msgpack.packb(
                    {'action': action, 'table': table, 'tm': tm}))

    def log_query(self, action, table, tm, count, sql, bt):
        self.broker.rpush(self._q_key(), msgpack.packb(
                {'method': self.method, 'call': self.id,
                    'action': action, 'table': table, 'tm': tm, 'count': count,
                    'sql': sql, 'bt': bt}))


select_pattern = re.compile('^SELECT .+ FROM "?([a-z_\-]+)"?.*')
insert_pattern = re.compile('^INSERT INTO "?([a-z_\-]+)"? .+')
update_pattern = re.compile('^UPDATE "?([a-z_\-]+)"? SET .+')
delete_pattern = re.compile('^DELETE FROM "?([a-z_\-]+)"?.*')
seq_pattern = re.compile('^SELECT NEXTVAL.+')


def parse_query(sql):
    r = select_pattern.search(sql)
    if r:
        return 'select', r.group(1)
    r = insert_pattern.search(sql)
    if r:
        return 'insert', r.group(1)
    r = update_pattern.search(sql)
    if r:
        return 'update', r.group(1)
    r = delete_pattern.search(sql)
    if r:
        return 'delete', r.group(1)
    r = seq_pattern.search(sql)
    if r:
        return 'seq', None
    return 'other', None


def analyze_before(cursor):
    if PerfLog().is_active():
        return cursor, time.time()


def analyze_after(cursor, start):
    p = PerfLog()
    tm = time.time() - start
    sql = cursor.query
    action, table = parse_query(sql)
    p.log_db(action, table, tm)
    if check_query(tm):
        # TODO: better format
        if action == 'select':
            count = cursor.rowcount
        else:
            count = 0
        bt = ''.join(traceback.format_stack()[-10:-2])
        p.log_query(action, table, tm, count, sql, bt)


def profile_before():
    p = PerfLog()
    if p.is_active() and check_profile(p.method):
        pr = Profile.Profile()
        pr.enable()
        return pr,


def profile_after(pr):
    p = PerfLog()
    pr.disable()
    s = StringIO.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
    ps.print_stats()
    # TODO: better format
    p.set_profile(s.getvalue())


def profile(func):
    def wrap(*args, **kwargs):
        try:
            context = profile_before()
        except:
            logger.exception('profile_before failed')
            context = None
        ret = func(*args, **kwargs)
        if context is not None:
            try:
                profile_after(*context)
            except:
                logger.exception('profile_after failed')
        return ret
    return wrap
