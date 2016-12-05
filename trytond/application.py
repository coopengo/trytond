# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import os
import logging

log_file = os.environ.get('WSGI_LOG_FILE')
if log_file:
    log_level = os.environ.get('LOG_LEVEL', 'ERROR')
    logging.basicConfig(level=getattr(logging, log_level),
        filename=log_file)

from trytond.pool import Pool
from trytond.wsgi import app

__all__ = ['app']

import trytond.protocols.dispatcher
