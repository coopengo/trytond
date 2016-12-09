# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from trytond.config import config
from trytond.exceptions import UserError, UserWarning, ConcurrencyException
from werkzeug.exceptions import Forbidden

logger = logging.getLogger(__name__)
sentry_dsn = config.get('sentry', 'dsn')


def sentry_wrap(func):
    client = None

    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (UserError, UserWarning, ConcurrencyException, Forbidden):
            raise
        except Exception:
            event_id = client.captureException()
            raise UserError(
                'An error occured\n\n'
                'Maintenance has been notified of this failure.\n'
                'In case you wish to discuss this issue with the team, please '
                'provide the following reference :\n\n%s' % event_id
                )
    if sentry_dsn:
        logger.info('setting sentry: %s' % sentry_dsn)
        from raven import Client
        client = Client(sentry_dsn)
        return wrap
    else:
        return func
