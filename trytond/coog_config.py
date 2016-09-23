# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
from trytond.config import config


def get_cache_redis():
    return config.get('cache', 'redis',
        default=os.environ.get('TRYTOND_CACHE_REDIS'))


def get_sentry_dsn():
    return config.get('sentry', 'dsn',
        default=os.environ.get('TRYTOND_SENTRY_DSN'))
