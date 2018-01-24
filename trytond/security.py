# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging

from trytond.pool import Pool
from trytond.config import config
from trytond.transaction import Transaction
from trytond import backend
from trytond.exceptions import LoginException

import security_redis as redis

logger = logging.getLogger(__name__)


def _get_pool(dbname):
    database_list = Pool.database_list()
    pool = Pool(dbname)
    if dbname not in database_list:
        pool.init()
    return pool


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
            except LoginException:
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
            redis.set_session(dbname, user_id, session.key)
            return user_id, session.key
    return


def logout(dbname, user, session):
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
                redis.del_session(dbname, user, session)
            except DatabaseOperationalError:
                if count:
                    continue
                raise
        return name


def check(dbname, user, session):
    return redis.has_session(dbname, user, session) and user


def reset(dbname, user, session):
    return redis.set_session(dbname, user, session)
