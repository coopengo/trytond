# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import datetime
from decimal import Decimal


class Default():
    pass


def freeze(o):
    if isinstance(o, (set, tuple, list)):
        return tuple(freeze(x) for x in o)
    elif isinstance(o, dict):
        return frozenset((x, freeze(y)) for x, y in o.iteritems())
    else:
        return o


def encode_hook(o):
    if isinstance(o, Decimal):
        return {
            '__decimal__': True,
            'data': str(o)
        }
    if isinstance(o, datetime.datetime):
        return {
            '__datetime__': True,
            'data': (o.year, o.month, o.day, o.hour, o.minute, o.second,
                o.microsecond)
        }
    if isinstance(o, datetime.date):
        return {
            '__date__': True,
            'data': (o.year, o.month, o.day)
        }
    if isinstance(o, datetime.time):
        return {
            '__time__': True,
            'data': (o.hour, o.minute, o.second, o.microsecond)
        }
    if isinstance(o, datetime.timedelta):
        return {
            '__timedelta__': True,
            'data': o.total_seconds()
        }
    if isinstance(o, set):
        return {
            '__set__': True,
            'data': tuple(o)
        }
    return o


def decode_hook(o):
    if '__decimal__' in o:
        return Decimal(o['data'])
    elif '__datetime__' in o:
        return datetime.datetime(*o['data'])
    elif '__date__' in o:
        return datetime.date(*o['data'])
    elif '__time__' in o:
        return datetime.time(*o['data'])
    elif '__timedelta__' in o:
        return datetime.timedelta(o['data'])
    elif '__set__' in o:
        return set(o['data'])
    return o
