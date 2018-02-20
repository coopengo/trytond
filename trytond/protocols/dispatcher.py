# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import http.client
import logging
import pydoc
import time

try:
    from http import HTTPStatus
except ImportError:
    from http import client as HTTPStatus
import traceback

from sql import Table
from werkzeug.exceptions import abort
from werkzeug.wrappers import Response

from trytond import __version__, backend, security
from trytond.config import config, get_hostname
from trytond.error_handling import error_wrap
from trytond.exceptions import (
    ConcurrencyException, LoginException, RateLimitException, TimeoutException,
    UserError, UserWarning)
from trytond.tools import is_instance_method
from trytond.transaction import Transaction
from trytond.worker import run_task
from trytond.wsgi import app

from .wrappers import with_pool

logger = logging.getLogger(__name__)

# JCA: log slow RPC (> log_time_threshold)
slow_threshold = config.getfloat('web', 'log_time_threshold', default=-1)
if slow_threshold >= 0:
    slow_logger = logging.getLogger('slowness')

ir_configuration = Table('ir_configuration')
ir_lang = Table('ir_lang')
ir_module = Table('ir_module')
res_user = Table('res_user')


# JCA: log slow RPC
def log_exception(method, *args, **kwargs):
    kwargs['exc_info'] = False
    method(*args, **kwargs)
    for elem in traceback.format_exc().split('\n'):
        method(elem)


@app.route('/<string:database_name>/', methods=['POST'])
def rpc(request, database_name):
    methods = {
        'common.db.login': login,
        'common.db.logout': logout,
        'system.listMethods': list_method,
        'system.methodHelp': help_method,
        'system.methodSignature': lambda *a: 'signatures not supported',
        }
    return methods.get(request.rpc_method, _dispatch)(
        request, database_name, *request.rpc_params)


def login(request, database_name, user, parameters, language=None):
    try:
        backend.Database(database_name).connect()
    except backend.DatabaseOperationalError:
        logger.error('fail to connect to %s', database_name, exc_info=True)
        abort(HTTPStatus.NOT_FOUND)
    context = {
        'language': language,
        '_request': request.context,
        }
    try:
        session = security.login(
            database_name, user, parameters, context=context)
        code = HTTPStatus.UNAUTHORIZED
    except RateLimitException:
        session = None
        code = HTTPStatus.TOO_MANY_REQUESTS
    if not session:
        abort(code)
    return session


@app.auth_required
def logout(request, database_name):
    auth = request.authorization
    security.logout(
        database_name, auth.get('userid'), auth.get('session'),
        context={'_request': request.context})


@app.route('/', methods=['POST'])
def root(request, *args):
    methods = {
        'common.server.version': lambda *a: __version__,
        'common.db.list': db_list,
        }
    return methods[request.rpc_method](request, *request.rpc_params)


@app.route('/', methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def options(request, path=None):
    return Response(status=HTTPStatus.NO_CONTENT)


def db_exist(request, database_name):
    try:
        backend.Database(database_name).connect()
        return True
    except Exception:
        return False


def db_list(request, *args):
    if not config.getboolean('database', 'list'):
        abort(HTTPStatus.FORBIDDEN)
    context = {'_request': request.context}
    hostname = get_hostname(request.host)
    with Transaction().start(
            None, 0, context=context, readonly=True, close=True,
            ) as transaction:
        return transaction.database.list(hostname=hostname)


@app.auth_required
@with_pool
def list_method(request, pool):
    methods = []
    for type in ('model', 'wizard', 'report'):
        for object_name, obj in pool.iterobject(type=type):
            for method in obj.__rpc__:
                methods.append(type + '.' + object_name + '.' + method)
    return methods


def get_object_method(request, pool):
    method = request.rpc_method
    type, _ = method.split('.', 1)
    name = '.'.join(method.split('.')[1:-1])
    method = method.split('.')[-1]
    return pool.get(name, type=type), method


@app.auth_required
@with_pool
def help_method(request, pool):
    obj, method = get_object_method(request, pool)
    return pydoc.getdoc(getattr(obj, method))


# AKE: hide tech exceptions and send them to sentry
@error_wrap
@app.auth_required
@with_pool
def _dispatch(request, pool, *args, **kwargs):

    obj, method = get_object_method(request, pool)
    if method in obj.__rpc__:
        rpc = obj.__rpc__[method]
    else:
        abort(HTTPStatus.FORBIDDEN)

    user = request.user_id
    session = None
    if request.authorization.type == 'session':
        session = request.authorization.get('session')

    if rpc.fresh_session and session:
        context = {'_request': request.context}
        if not security.check_timeout(
                pool.database_name, user, session, context=context):
            abort(http.client.UNAUTHORIZED)

    log_message = '%s.%s(*%s, **%s) from %s@%s%s'
    username = request.authorization.username
    if isinstance(username, bytes):
        username = username.decode('utf-8')
    log_args = (
        obj, method, args, kwargs, username, request.remote_addr, request.path)
    logger.debug(log_message, *log_args)

    # JCA: log slow RPC
    if slow_threshold >= 0:
        slow_msg = '%s.%s (%s s)'
        slow_args = (obj, method)
        slow_start = time.time()

    user = request.user_id

    # AKE: add session to transaction context
    if request.authorization.type == 'session':
        session = request.authorization.get('session')
        party = None
    elif request.authorization.type == 'token':
        session = request.authorization.get('token')
        party = request.authorization.get('party_id')

    retry = config.getint('database', 'retry')
    for count in range(retry, -1, -1):
        with Transaction().start(pool.database_name, user,
                readonly=rpc.readonly, timeout=rpc.timeout) as transaction:
            try:
                c_args, c_kwargs, transaction.context, transaction.timestamp \
                    = rpc.convert(obj, *args, **kwargs)
                transaction.context['_request'] = request.context
                meth = getattr(obj, method)
                if (rpc.instantiate is None
                        or not is_instance_method(obj, method)):
                    result = rpc.result(meth(*c_args, **c_kwargs))
                else:
                    assert rpc.instantiate == 0
                    inst = c_args.pop(0)
                    if hasattr(inst, method):
                        result = rpc.result(meth(inst, *c_args, **c_kwargs))
                    else:
                        result = [rpc.result(meth(i, *c_args, **c_kwargs))
                            for i in inst]
            except backend.DatabaseTimeoutError as exception:
                logger.debug(log_message, *log_args, exc_info=True)
                raise TimeoutException from exception
            except backend.DatabaseOperationalError:
                if count and not rpc.readonly:
                    transaction.rollback()
                    continue
                logger.error(log_message, *log_args, exc_info=True)

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.error, slow_msg, *slow_args)

                raise
            except (ConcurrencyException, UserError, UserWarning,
                    LoginException):
                logger.debug(log_message, *log_args, exc_info=True)

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.debug, slow_msg, *slow_args)

                raise
            except Exception:
                logger.error(log_message, *log_args, exc_info=True)

                # JCA: log slow RPC
                if slow_threshold >= 0:
                    slow_args += (str(time.time() - slow_start),)
                    log_exception(slow_logger.error, slow_msg, *slow_args)

                raise
            # Need to commit to unlock SQLite database
            transaction.commit()
        while transaction.tasks:
            task_id = transaction.tasks.pop()
            run_task(pool, task_id)
        if session:
            context = {'_request': request.context}
            security.reset(pool.database_name, session, context=context)

        # JCA: log slow RPC
        if slow_threshold >= 0:
            slow_diff = time.time() - slow_start
            slow_args += (str(slow_diff),)
            if slow_diff > slow_threshold:
                slow_logger.info(slow_msg, *slow_args)
            else:
                slow_logger.debug(slow_msg, *slow_args)

        response = app.make_response(request, result)
        if rpc.readonly and rpc.cache:
            response.headers.extend(rpc.cache.headers())
        return response
