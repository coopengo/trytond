import datetime
from decimal import Decimal
import msgpack


__all__ = ['pack', 'unpack']


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


def pack(value):
    return msgpack.packb(value, use_bin_type=True, default=encode_hook)


def unpack(bundle):
    return msgpack.unpackb(bundle, encoding='utf-8', object_hook=decode_hook)
