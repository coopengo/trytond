# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
# AKE: manage session on redis
from threading import Lock
import redis
from urlparse import urlparse

from trytond.config import config

_client = None
_client_lock = Lock()


def get_client():
    global _client, _client_lock
    with _client_lock:
        if _client is None:
            redis_uri = config.get('session', 'redis')
            assert redis_uri, 'redis uri not set'
            url = urlparse(redis_uri)
            assert url.scheme == 'redis', 'invalid redis url'
            host = url.hostname
            port = url.port
            db = url.path.strip('/')
            _client = redis.StrictRedis(host=host, port=port, db=db)
    return _client


def key(dbname, user, session):
    return 'session:%s:%d:%s' % (dbname, user, session)


def set_session(dbname, user, session, login):
    k = key(dbname, user, session)
    ttl = config.getint('session', 'timeout')
    return get_client().setex(k, ttl, login)


def hit_session(dbname, user, session):
    k = key(dbname, user, session)
    ttl = config.getint('session', 'timeout')
    return get_client().expire(k, ttl)


def get_session(dbname, user, session):
    k = key(dbname, user, session)
    return get_client().get(k)


def del_session(dbname, user, session):
    k = key(dbname, user, session)
    return get_client().delete(k)


def count_sessions(dbname, user):
    res = 0
    c = get_client()
    ks = key(dbname, user, '*')
    for k in c.scan_iter(ks):
        res += 1
    return res


def del_sessions(dbname, user):
    c = get_client()
    ks = key(dbname, user, '*')
    for k in c.scan_iter(ks):
        c.delete(k)
