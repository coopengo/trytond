# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import xmlrpc.client as client
import datetime
import logging

# convert decimal to float before marshalling:
from decimal import Decimal

from werkzeug.wrappers import Response
from werkzeug.exceptions import (
    BadRequest, InternalServerError, Conflict, Forbidden, Locked,
    TooManyRequests)

from trytond.model.fields.dict import ImmutableDict
from trytond.protocols.wrappers import Request
from trytond.exceptions import (
    TrytonException, UserWarning, LoginException, ConcurrencyException,
    RateLimitException, MissingDependenciesException)
from trytond.tools import cached_property

logger = logging.getLogger(__name__)


def dump_decimal(self, value, write):
    value = {'__class__': 'Decimal',
        'decimal': str(value),
        }
    self.dump_struct(value, write)


def dump_date(self, value, write):
    value = {'__class__': 'date',
        'year': value.year,
        'month': value.month,
        'day': value.day,
        }
    self.dump_struct(value, write)


def dump_time(self, value, write):
    value = {'__class__': 'time',
        'hour': value.hour,
        'minute': value.minute,
        'second': value.second,
        'microsecond': value.microsecond,
        }
    self.dump_struct(value, write)


def dump_timedelta(self, value, write):
    value = {'__class__': 'timedelta',
        'seconds': value.total_seconds(),
        }
    self.dump_struct(value, write)


def dump_long(self, value, write):
    try:
        self.dump_long(value, write)
    except OverflowError:
        write('<value><biginteger>')
        write(str(int(value)))
        write('</biginteger></value>\n')


client.Marshaller.dispatch[Decimal] = dump_decimal
client.Marshaller.dispatch[datetime.date] = dump_date
client.Marshaller.dispatch[datetime.time] = dump_time
client.Marshaller.dispatch[datetime.timedelta] = dump_timedelta
client.Marshaller.dispatch[int] = dump_long


def dump_struct(self, value, write, escape=client.escape):
    converted_value = {}
    for k, v in value.items():
        if isinstance(k, int):
            k = str(k)
        elif isinstance(k, float):
            k = repr(k)
        converted_value[k] = v
    return self.dump_struct(converted_value, write, escape=escape)


client.Marshaller.dispatch[dict] = dump_struct
client.Marshaller.dispatch[ImmutableDict] = dump_struct


class XMLRPCDecoder(object):

    decoders = {}

    @classmethod
    def register(cls, klass, decoder):
        assert klass not in cls.decoders
        cls.decoders[klass] = decoder

    def __call__(self, dct):
        if dct.get('__class__') in self.decoders:
            return self.decoders[dct['__class__']](dct)
        return dct


XMLRPCDecoder.register('date',
    lambda dct: datetime.date(dct['year'], dct['month'], dct['day']))
XMLRPCDecoder.register('time',
    lambda dct: datetime.time(dct['hour'], dct['minute'], dct['second'],
        dct['microsecond']))
XMLRPCDecoder.register('timedelta',
    lambda dct: datetime.timedelta(seconds=dct['seconds']))
XMLRPCDecoder.register('Decimal', lambda dct: Decimal(dct['decimal']))


def end_struct(self, data):
    mark = self._marks.pop()
    # map structs to Python dictionaries
    dct = {}
    items = self._stack[mark:]
    for i in range(0, len(items), 2):
        dct[items[i]] = items[i + 1]
    dct = XMLRPCDecoder()(dct)
    self._stack[mark:] = [dct]
    self._value = 0


client.Unmarshaller.dispatch['struct'] = end_struct


class XMLRequest(Request):
    parsed_content_type = 'xml'

    @cached_property
    def parsed_data(self):
        if self.parsed_content_type in self.environ.get('CONTENT_TYPE', ''):
            try:
                # TODO replace by own loads
                return client.loads(self.decoded_data, use_builtin_types=True)
            except Exception:
                raise BadRequest('Unable to read XMl request')
        else:
            raise BadRequest('Not an XML request')

    @property
    def rpc_method(self):
        return self.parsed_data[1]

    @property
    def rpc_params(self):
        return self.parsed_data[0]


class XMLProtocol:
    content_type = 'xml'

    @classmethod
    def request(cls, environ):
        return XMLRequest(environ)

    @classmethod
    def response(cls, data, request):
        if isinstance(request, XMLRequest):
            if isinstance(data, TrytonException):
                data = client.Fault(data.code, str(data))
            elif isinstance(data, Exception):
                data = client.Fault(255, str(data))
            else:
                data = (data,)
            return Response(client.dumps(
                    data, methodresponse=True, allow_none=True),
                content_type='text/xml')
        else:
            if isinstance(data, UserWarning):
                return Conflict(data)
            elif isinstance(data, LoginException):
                return Forbidden(data)
            elif isinstance(data, ConcurrencyException):
                return Locked(data)
            elif isinstance(data, RateLimitException):
                return TooManyRequests(data)
            elif isinstance(data, MissingDependenciesException):
                return InternalServerError(data)
            elif isinstance(data, TrytonException):
                return BadRequest(data)
            elif isinstance(data, Exception):
                return InternalServerError(data)
            return Response(data)
