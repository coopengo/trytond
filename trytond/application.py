# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import csv
import os
import logging
import threading
from io import StringIO

try:
    import uwsgidecorators
except ImportError:
    uwsgidecorators = None

__all__ = ['app']

LF = '%(process)s %(thread)s [%(asctime)s] %(levelname)s %(name)s %(message)s'
log_file = os.environ.get('WSGI_LOG_FILE')
log_level = os.environ.get('LOG_LEVEL', 'ERROR')
if log_file:
    logging.basicConfig(level=getattr(logging, log_level), format=LF,
        filename=log_file)

if not log_file:
    # Logging must be set before importing
    logging_config = os.environ.get('TRYTOND_LOGGING_CONFIG')
    if logging_config:
        import logging.config
        logging.config.fileConfig(logging_config)
    else:
        logging.basicConfig(level=getattr(logging, log_level), format=LF)

if os.environ.get('TRYTOND_COROUTINE'):
    from gevent import monkey
    monkey.patch_all()

from trytond.pool import Pool
from trytond.wsgi import app

Pool.start()
# TRYTOND_CONFIG it's managed by importing config
db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
if db_names:
    # Read with csv so database name can include special chars
    reader = csv.reader(StringIO(db_names))
    for db_name in next(reader):
        Pool(db_name).init()


if uwsgidecorators is not None:
    # When running under uwsgi, the behaviour will be to fork the application
    # process once it is loaded.
    # If database names were provided, the cache / iwc listener will be
    # initialized before forking, and the actual fork will break them.
    #
    # So we need to:
    #   - Remove those threads from the master process, which will not need
    #   them anyway
    #   - Manually fix them after each fork so they are properly set
    #   on each worker

    from trytond.cache import Cache
    from trytond import iwc
    from trytond.bus import Bus

    Cache._listener_lock = threading.Lock()
    Cache._listener.clear()

    iwc.Listener._listener_lock = threading.Lock()
    iwc.Listener._listener.clear()

    Bus._queues_lock = threading.Lock()
    Bus._queues.clear()

    @uwsgidecorators.postfork
    def reset_application_threads():
        import logging
        from trytond.cache import Cache
        from trytond import iwc
        from trytond.bus import Bus

        db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
        if db_names:
            logging.getLogger('uwsgi').info('Postfork Triggered')
            # Read with csv so database name can include special chars
            reader = csv.reader(StringIO(db_names))
            Cache._listener_lock = threading.Lock()
            Cache._listener.clear()

            iwc.Listener._listener_lock = threading.Lock()
            iwc.Listener._listener.clear()

            Bus._queues_lock = threading.Lock()
            Bus._queues.clear()

            from trytond.transaction import Transaction
            for name in next(reader):
                iwc.start(name)
                with Transaction().start(name, 0) as transaction:
                    Cache.sync(transaction)


application = app
