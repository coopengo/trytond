# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
import smtplib
import urllib
from email.message import Message
from urlparse import parse_qs

from .config import config, parse_uri
from .transaction import Transaction

__all__ = ['sendmail_transactional', 'sendmail', 'SMTPDataManager']
logger = logging.getLogger(__name__)


def sendmail_transactional(
        from_addr, to_addrs, msg, transaction=None, datamanager=None):
    if transaction is None:
        transaction = Transaction()
    assert isinstance(transaction, Transaction), transaction
    if datamanager is None:
        datamanager = SMTPDataManager()
    datamanager = transaction.join(datamanager)
    datamanager.put(from_addr, to_addrs, msg)


def sendmail(from_addr, to_addrs, msg, server=None):
    if server is None:
        server = get_smtp_server()
        quit = True
    else:
        quit = False
    try:
        senderrs = server.sendmail(from_addr, to_addrs, msg.as_string())
    except smtplib.SMTPException:
        logger.error('fail to send email', exc_info=True)
    else:
        if senderrs:
            logger.warn('fail to send email to %s', senderrs)
    if quit:
        server.quit()


def get_smtp_server(uri=None):
    if uri is None:
        uri = config.get('email', 'uri')
    uri = parse_uri(uri)
    extra = {}
    if uri.query:
        cast = {'timeout': int}
        for key, value in parse_qs(uri.query, strict_parsing=True).iteritems():
            extra[key] = cast.get(key, lambda a: a)(value[0])
    if uri.scheme.startswith('smtps'):
        server = smtplib.SMTP_SSL(uri.hostname, uri.port, **extra)
    else:
        server = smtplib.SMTP(uri.hostname, uri.port, **extra)

    if 'tls' in uri.scheme:
        server.starttls()

    if uri.username and uri.password:
        server.login(
            urllib.unquote_plus(uri.username),
            urllib.unquote_plus(uri.password))
    return server


class SMTPDataManager(object):

    def __init__(self, uri=None):
        self.uri = uri
        self.queue = []
        self._server = None

    def put(self, from_addr, to_addrs, msg):
        assert isinstance(msg, Message), msg
        self.queue.append((from_addr, to_addrs, msg))

    def __eq__(self, other):
        if not isinstance(other, SMTPDataManager):
            return NotImplemented
        return self.uri == other.uri

    def abort(self, trans):
        self._finish()

    def tpc_begin(self, trans):
        pass

    def commit(self, trans):
        pass

    def tpc_vote(self, trans):
        if self._server is None:
            self._server = get_smtp_server(self.uri)

    def tpc_finish(self, trans):
        if self._server is not None:
            for from_addr, to_addrs, msg in self.queue:
                sendmail(from_addr, to_addrs, msg, server=self._server)
            self._server.quit()
            self._finish()

    def tpc_abort(self, trans):
        if self._server:
            self._server.close()
        self._finish()

    def _finish(self):
        self._server = None
        self.queue = []
