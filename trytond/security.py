# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging

from trytond.pool import Pool
from trytond.config import config
from trytond.transaction import Transaction
from trytond import backend
from trytond.exceptions import LoginException, RateLimitException

import trytond.security_redis as redis

logger = logging.getLogger(__name__)


def _get_pool(dbname):
    database_list = Pool.database_list()
    pool = Pool(dbname)
    if dbname not in database_list:
        pool.init()
    return pool


# AKE: manage session on redis
def config_session_redis():
    return config.get('session', 'redis', default=None)


# AKE: manage session on redis
def config_session_exclusive():
    return config.getboolean('session', 'exclusive', default=True)


# AKE: manage session on redis
def config_session_audit():
    return config.getboolean('session', 'audit', default=True)


def _get_remote_addr(context):
    if context and '_request' in context:
        return context['_request'].get('remote_addr')


def login(dbname, loginname, parameters, cache=True, context=None):
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    for count in range(config.getint('database', 'retry'), -1, -1):
        with Transaction().start(dbname, 0, context=context) as transaction:
            pool = _get_pool(dbname)
            User = pool.get('res.user')
            try:
                user_id = User.get_login(loginname, parameters)
            except DatabaseOperationalError:
                if count:
                    continue
                raise
            except (LoginException, RateLimitException):
                # Let's store any changes done
                transaction.commit()
                raise
        break
    session = None
    if user_id:
        if not cache:
            session = user_id
        else:
            with Transaction().start(dbname, user_id):
                Session = pool.get('ir.session')
                session = user_id, Session.new()
                # AKE: manage session on redis
                if config_session_redis():
                    if config_session_exclusive():
                        redis.del_sessions(dbname, user_id)
                    redis.set_session(dbname, user_id, session.key, loginname)

        logger.info("login succeeded for '%s' from '%s' on database '%s'",
            loginname, _get_remote_addr(context), dbname)
    else:
        logger.error("login failed for '%s' from '%s' on database '%s'",
            loginname, _get_remote_addr(context), dbname)
    return session


def logout(dbname, user, session, context=None):
    # AKE: manage session on redis
    if config_session_redis():
        name = redis.get_session(dbname, user, session)
        if name:
            redis.del_session(dbname, user, session)
        return name
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    for count in range(config.getint('database', 'retry'), -1, -1):
        with Transaction().start(dbname, 0, context=context):
            pool = _get_pool(dbname)
            Session = pool.get('ir.session')
            try:
                name = Session.remove(session)
            except DatabaseOperationalError:
                if count:
                    continue
                raise
    logger.info("logout for '%s' from '%s' on database '%s'",
        name, _get_remote_addr(context), dbname)


def check(dbname, user, session, context=None):
    # AKE: manage session on redis
    if config_session_redis():
        ttl = redis.hit_session(dbname, user, session)
        if ttl is not None:
            if config_session_audit():
                redis.time_user(dbname, user, ttl)
            return user
        return
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    for count in range(config.getint('database', 'retry'), -1, -1):
        with Transaction().start(dbname, user, context=context) as transaction:
            pool = _get_pool(dbname)
            Session = pool.get('ir.session')
            try:
                find = Session.check(user, session)
                break
            except DatabaseOperationalError:
                if count:
                    continue
                raise
            finally:
                transaction.commit()
    if find is None:
        logger.error("session failed for '%s' from '%s' on database '%s'",
            user, _get_remote_addr(context), dbname)
        return
    elif not find:
        logger.info("session expired for '%s' from '%s' on database '%s'",
            user, _get_remote_addr(context), dbname)
        return
    else:
        logger.debug("session valid for '%s' from '%s' on database '%s'",
            user, _get_remote_addr(context), dbname)
        return user


def check_token(dbname, token):
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    for count in range(config.getint('database', 'retry'), -1, -1):
        with Transaction().start(dbname, 0, readonly=True):
            pool = _get_pool(dbname)
            Token = pool.get('api.token')
            try:
                return Token.check(token)
            except DatabaseOperationalError:
                if count:
                    continue
                raise


def reset(dbname, user, session):
    # AKE: manage session on redis
    if config_session_redis():
        ttl = redis.hit_session(dbname, user, session)
        if ttl is not None and config_session_audit():
            redis.time_user(dbname, user, ttl)
        return
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    try:
        with Transaction().start(dbname, 0):
            pool = _get_pool(dbname)
            Session = pool.get('ir.session')
            Session.reset(session)
    except DatabaseOperationalError:
        pass
