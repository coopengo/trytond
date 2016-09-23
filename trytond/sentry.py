# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from trytond.coog_config import get_sentry_dsn
from trytond.exceptions import UserError, UserWarning, ConcurrencyException

logger = logging.getLogger(__name__)
sentry_dsn = get_sentry_dsn()


def sentry_wrap(func):
    client = None

    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (UserError, UserWarning, ConcurrencyException):
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
