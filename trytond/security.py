# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.config import config
from trytond.transaction import Transaction
from trytond import backend
from trytond.exceptions import LoginException, RateLimitException

import trytond.security_redis as redis


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


def login(dbname, loginname, parameters, cache=True, language=None):
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    context = {'language': language}
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
    if user_id:
        if not cache:
            return user_id
        with Transaction().start(dbname, user_id):
            Session = pool.get('ir.session')
            session, = Session.create([{}])
            # AKE: manage session on redis
            if config_session_redis():
                if config_session_exclusive():
                    redis.del_sessions(dbname, user_id)
                redis.set_session(dbname, user_id, session.key, loginname)
            return user_id, session.key
    return


def logout(dbname, user, session):
    # AKE: manage session on redis
    if config_session_redis():
        name = redis.get_session(dbname, user, session)
        if name:
            redis.del_session(dbname, user, session)
        return name
    DatabaseOperationalError = backend.get('DatabaseOperationalError')
    for count in range(config.getint('database', 'retry'), -1, -1):
        with Transaction().start(dbname, 0):
            pool = _get_pool(dbname)
            Session = pool.get('ir.session')
            try:
                sessions = Session.search([
                        ('key', '=', session),
                        ])
                if not sessions:
                    return
                session, = sessions
                name = session.create_uid.login
                Session.delete(sessions)
            except DatabaseOperationalError:
                if count:
                    continue
                raise
        return name


def check(dbname, user, session):
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
        with Transaction().start(dbname, user) as transaction:
            pool = _get_pool(dbname)
            Session = pool.get('ir.session')
            try:
                if not Session.check(user, session):
                    return
                else:
                    return user
            except DatabaseOperationalError:
                if count:
                    continue
                raise
            finally:
                transaction.commit()


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
