# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys
import logging
from trytond.config import config
from trytond.exceptions import UserError, UserWarning, ConcurrencyException
from werkzeug.exceptions import Forbidden

logger = logging.getLogger(__name__)
sentry_dsn = config.get('sentry', 'dsn')
client = None


class SentryError(UserError):
    '''
    Sentry-Wrapped User Error
    '''
    __slots__ = ('event_id', 'original_error')

    def __init__(self, message, event_id):
        super().__init__(message)
        self.event_id = event_id
        self.original_error = sys.exc_info()


def handle_exception(e: Exception, reraise=True) -> Exception:
    '''
    Handles an exception, sending it to the configured Sentry instance if
    appliable.

    Setting the "reraise" flag to False can be used to manually handle the
    Sentry exception
    '''
    if not sentry_dsn:
        if reraise:
            raise
        return e

    global client
    from sentry_sdk import capture_exception
    if client is None:
        from sentry_sdk import init
        logger.info('setting sentry: %s' % sentry_dsn)
        init(sentry_dsn)

    event_id = capture_exception(e)
    sentry_error = SentryError(
        'An error occured\n\n'
        'Maintenance has been notified of this failure.\n'
        'In case you wish to discuss this issue with the team, please '
        'provide the following reference :\n\n%s' % event_id,
        event_id)
    if reraise:
        raise sentry_error
    return sentry_error


def sentry_wrap(func):
    '''
    A decorator that can be placed on a function to use Sentry as error
    backend, if it is configured
    '''
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (UserError, UserWarning, ConcurrencyException, Forbidden):
            raise
        except Exception as e:
            handle_exception(e)

    if not sentry_dsn:
        return func
    return wrap
