# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import base64
import gzip
import logging
import time
from io import BytesIO
from functools import wraps
try:
    from http import HTTPStatus
except ImportError:
    from http import client as HTTPStatus

from werkzeug.wrappers import Request as _Request, Response
from werkzeug.utils import cached_property
from werkzeug.http import wsgi_to_bytes, bytes_to_wsgi
from werkzeug.datastructures import Authorization
from werkzeug.exceptions import abort, HTTPException

from trytond import security, backend
from trytond.exceptions import RateLimitException
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.config import config, parse_uri

logger = logging.getLogger(__name__)


class Request(_Request):

    view_args = None

    @property
    def decoded_data(self):
        if self.content_encoding == 'gzip':
            zipfile = gzip.GzipFile(fileobj=BytesIO(self.data), mode='rb')
            return zipfile.read()
        else:
            return self.data

    @property
    def parsed_data(self):
        return self.data

    @property
    def rpc_method(self):
        return

    @property
    def rpc_params(self):
        return

    @cached_property
    def authorization(self):
        authorization = super(Request, self).authorization
        if authorization is None:
            header = self.environ.get('HTTP_AUTHORIZATION')
            auth = parse_authorization_header(header)
            if auth and auth.type == 'token':
                database_name = self.view_args.get('database_name')
                if not database_name:
                    return None
                user_id, party_id = security.check_token(
                    database_name, auth.get('token'))
                return Authorization('token', {
                        'token': auth.get('token'),
                        'user_id': user_id,
                        'party_id': party_id
                    })
            else:
                return auth
        return authorization

    @cached_property
    def user_id(self):
        database_name = self.view_args.get('database_name')
        if not database_name:
            return None
        auth = self.authorization
        if not auth:
            return None
        context = {'_request': self.context}
        if auth.type == 'session':
            user_id = security.check(
                database_name, auth.get('userid'), auth.get('session'),
                context=context)
        elif auth.type == 'token':
            user_id = auth.get('user_id')
        else:
            try:
                user_id = security.login(
                    database_name, auth.username, auth, cache=False,
                    context=context)
            except RateLimitException:
                abort(HTTPStatus.TOO_MANY_REQUESTS)
        return user_id

    @cached_property
    def context(self):
        return {
            'remote_addr': self.remote_addr,
            'http_host': self.environ.get('HTTP_HOST'),
            'scheme': self.scheme,
            'is_secure': self.is_secure,
            }


def parse_authorization_header(value):
    if not value:
        return
    value = wsgi_to_bytes(value)
    try:
        auth_type, auth_info = value.split(None, 1)
        auth_type = auth_type.lower()
    except ValueError:
        return
    if auth_type == b'session':
        try:
            username, userid, session = base64.b64decode(auth_info).split(
                b':', 3)
            userid = int(userid)
        except Exception:
            return
        return Authorization('session', {
                'username': bytes_to_wsgi(username),
                'userid': userid,
                'session': bytes_to_wsgi(session),
                })
    # JMO: the initial implementation used 'token',
    # but the IETF specifies 'Bearer'
    # (cf https://datatracker.ietf.org/doc/html/rfc6750#section-2.1 ).
    # So, we allow both to maintain compatibility with previous uses,
    # and be compatible with standard HTTP clients.
    elif auth_type in (b'token', b'bearer'):
        return Authorization('token', {'token': bytes_to_wsgi(auth_info)})


def set_max_request_size(size):
    def decorator(func):
        func.max_request_size = size
        return func
    return decorator


def with_pool(func):
    @wraps(func)
    def wrapper(request, database_name, *args, **kwargs):
        database_list = Pool.database_list()
        pool = Pool(database_name)
        if database_name not in database_list:
            with Transaction().start(database_name, 0, readonly=True):
                pool.init()
        return func(request, pool, *args, **kwargs)
    return wrapper


def with_pool_by_config(func):
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        uri = config.get('database', 'uri')
        database_name = parse_uri(uri).path[1:]
        return with_pool(func)(request, database_name, *args, **kwargs)
    return wrapper


def with_transaction(readonly=None, user=0, context=None):
    from trytond.worker import run_task

    def decorator(func):
        @wraps(func)
        def wrapper(request, pool, *args, **kwargs):
            nonlocal user, context
            readonly_ = readonly  # can not modify non local
            if readonly_ is None:
                if request.method in {'POST', 'PUT', 'DELETE', 'PATCH'}:
                    readonly_ = False
                else:
                    readonly_ = True
            if context is None:
                context = {}
            else:
                context = context.copy()
            context['_request'] = request.context
            if user == 'request':
                user = request.user_id
            retry = config.getint('database', 'retry')
            for count in range(retry, -1, -1):
                if count != retry:
                    time.sleep(0.02 * (retry - count))
                with Transaction().start(
                        pool.database_name, user, readonly=readonly_,
                        context=context) as transaction:
                    try:
                        result = func(request, pool, *args, **kwargs)
                    except backend.DatabaseOperationalError:
                        if count and not readonly_:
                            transaction.rollback()
                            continue
                        logger.error('%s', request, exc_info=True)
                        raise
                    except Exception:
                        logger.error('%s', request, exc_info=True)
                        raise
                    # Need to commit to unlock SQLite database
                    transaction.commit()
                while transaction.tasks:
                    task_id = transaction.tasks.pop()
                    run_task(pool, task_id)
                return result
        return wrapper
    return decorator


def user_application(name, json=True):
    from .jsonrpc import JSONEncoder, json as json_

    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            pool = Pool()
            UserApplication = pool.get('res.user.application')

            authorization = wsgi_to_bytes(request.headers['Authorization'])
            try:
                auth_type, auth_info = authorization.split(None, 1)
                auth_type = auth_type.lower()
            except ValueError:
                abort(HTTPStatus.UNAUTHORIZED)
            if auth_type != b'bearer':
                abort(HTTPStatus.FORBIDDEN)

            application = UserApplication.check(bytes_to_wsgi(auth_info), name)
            if not application:
                abort(HTTPStatus.FORBIDDEN)
            transaction = Transaction()
            # TODO language
            with transaction.set_user(application.user.id), \
                    transaction.set_context(_check_access=True):
                try:
                    response = func(request, *args, **kwargs)
                except Exception as e:
                    if isinstance(e, HTTPException):
                        raise
                    logger.error('%s', request, exc_info=True)
                    abort(HTTPStatus.INTERNAL_SERVER_ERROR, e)
            if not isinstance(response, Response) and json:
                response = Response(json_.dumps(response, cls=JSONEncoder),
                    content_type='application/json')
            return response
        return wrapper
    return decorator
