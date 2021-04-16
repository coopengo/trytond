# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import copy
import datetime as dt
import inspect
from inspect import Parameter

from trytond.transaction import Transaction

__all__ = ['RPC']


class RPC(object):
    '''Define RPC behavior

    readonly: The transaction mode
    instantiate: The position or the slice of the arguments to be instanciated
    result: The function to transform the result
    check_access: If access right must be checked
    fresh_session: If a fresh session is required
    unique: Check instances are unique
    rate_limitations: A dictionary of function used to impose rate limitation
                      on incoming parameters
    '''

    __slots__ = ('readonly', 'instantiate', 'result', 'check_access',
        'fresh_session', 'unique', 'cache', 'rate_limitations')

    def __init__(self, readonly=True, instantiate=None, result=None,
            check_access=True, fresh_session=False, unique=True, cache=None,
            rate_limitations=None):
        self.readonly = readonly
        self.instantiate = instantiate
        if result is None:
            def result(r):
                return r
        self.result = result
        self.check_access = check_access
        self.fresh_session = fresh_session
        self.unique = unique
        if cache:
            if not isinstance(cache, RPCCache):
                cache = RPCCache(**cache)
        self.cache = cache
        self.rate_limitations = rate_limitations or {}

    def convert(self, obj, *args, **kwargs):
        args = list(args)
        kwargs = kwargs.copy()
        if 'context' in kwargs:
            context = kwargs.pop('context')
            if not isinstance(context, dict):
                raise TypeError("context must be a dictionary")
        else:
            try:
                context = args.pop()
            except IndexError:
                context = None
            if not isinstance(context, dict):
                raise ValueError("Missing context argument")
        context = copy.deepcopy(context)
        timestamp = None
        for key in list(context.keys()):
            if key == '_timestamp':
                timestamp = context[key]
            # Remove all private keyword but _datetime for history
            if key.startswith('_') and not key.startswith('_datetime'):
                del context[key]
        if self.instantiate is not None:

            def instance(data):
                with Transaction().set_context(context):
                    if isinstance(data, int):
                        return obj(data)
                    elif isinstance(data, dict):
                        return obj(**data)
                    else:
                        if self.unique and len(data) != len(set(data)):
                            raise ValueError("Duplicate ids")
                        return obj.browse(data)
            if isinstance(self.instantiate, slice):
                for i, data in enumerate(args[self.instantiate]):
                    start, _, step = self.instantiate.indices(len(args))
                    i = i * step + start
                    args[i] = instance(data)
            else:
                data = args[self.instantiate]
                args[self.instantiate] = instance(data)
        if self.check_access:
            context['_check_access'] = True
        return args, kwargs, context, timestamp

    def apply_limitations(self, method, c_args, c_kwargs):
        signature = inspect.signature(method)
        bounded = signature.bind(*c_args, **c_kwargs)
        bounded.apply_defaults()

        n_args, n_kwargs = [], {}
        for name, value in bounded.arguments.items():
            if name in self.rate_limitations:
                value = self.rate_limitations[name](value)

            kind = signature.parameters[name].kind
            if kind == Parameter.POSITIONAL_ONLY:
                n_args.append(value)
            elif kind == Parameter.VAR_POSITIONAL:
                n_args.extend(value)
            elif kind == Parameter.POSITIONAL_OR_KEYWORD:
                n_args.append(value)
            elif kind == Parameter.KEYWORD_ONLY:
                n_kwargs[name] = value
            elif kind == Parameter.VAR_KEYWORD:
                n_kwargs.update(value)

        return n_args, n_kwargs


class RPCCache:
    __slots__ = ('duration',)

    def __init__(self, days=0, seconds=0):
        self.duration = dt.timedelta(days=days, seconds=seconds)

    def headers(self):
        return {
            'X-Tryton-Cache': int(self.duration.total_seconds()),
            }
