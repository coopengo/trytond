# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from trytond.config import config

from .error_handling import ErrorHandler

logger = logging.getLogger(__name__)
sentry_dsn = config.get('sentry', 'dsn')
init_done = False


class SentryErrorHandler(ErrorHandler):
    '''
    Error handler that stores the error information in a sentry backend
    '''
    _message = '''An error occured

Maintenance has been notified of this failure.
You can create an issue at https://support.coopengo.com.
Please provide the following reference:

{}'''

    @classmethod
    def do_handle_exception(cls, e):
        from sentry_sdk import capture_exception
        cls._init_sentry()
        return capture_exception(e)

    @staticmethod
    def _init_sentry():
        global init_done
        if not init_done:
            from sentry_sdk import init
            logger.info('setting sentry: %s' % sentry_dsn)
            init(sentry_dsn)
            init_done = True
