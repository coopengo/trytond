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

__all__ = ['app', 'application']

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
logging.captureWarnings(True)

if os.environ.get('TRYTOND_COROUTINE'):
    from gevent import monkey
    monkey.patch_all()

from trytond.pool import Pool  # noqa: E402
from trytond.wsgi import app  # noqa: E402

Pool.start()
# TRYTOND_CONFIG it's managed by importing config
db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
if db_names:
    # Read with csv so database name can include special chars
    reader = csv.reader(StringIO(db_names))
    threads = []
    for name in next(reader):
        thread = threading.Thread(target=Pool(name).init)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()


if uwsgidecorators is not None:
    # When running under uwsgi, the behaviour will be to fork the application
    # process once it is loaded.
    # If database names were provided, the cache / iwc listener will be
    # initialized before forking, and the actual fork will break them.
    #
    # So we need to manually fix them after each fork so they are properly set
    # on each worker
    @uwsgidecorators.postfork
    def preload():
        from trytond.cache import Cache
        from trytond import iwc
        from trytond.transaction import Transaction
        db_names = os.environ.get('TRYTOND_DATABASE_NAMES')
        if db_names:
            # Read with csv so database name can include special chars
            reader = csv.reader(StringIO(db_names))
            Cache._listener.clear()
            iwc.Listener._listener.clear()
            for name in next(reader):
                iwc.start(name)
                with Transaction().start(name, 0) as transaction:
                    Cache.sync(transaction)


application = app
