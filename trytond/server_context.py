# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import logging
from threading import local


__all__ = [
    'ServerContext',
    ]


class _AttributeManager(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return ServerContext()

    def __exit__(self, type, value, traceback):
        context = ServerContext()
        for name, value in self.kwargs.iteritems():
            setattr(context, name, value)


class _Local(local):
    instance = None


class ServerContext(object):
    'Trytond context controller'
    _local = _Local()

    def __new__(cls):
        instance = cls._local.instance
        if not instance:
            cls._local.instance = super(ServerContext, cls).__new__(cls)
            logging.getLogger().debug('New Server Context instance created')
            cls._local.instance.context = {}
        return cls._local.instance

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._local.instance = None

    def get(self, *args, **kwargs):
        return self.context.get(*args, **kwargs)

    def set_context(self, context=None, **kwargs):
        if context is None:
            context = {}
        manager = _AttributeManager(context=self.context)
        self.context = self.context.copy()
        self.context.update(context)
        if kwargs:
            self.context.update(kwargs)
        return manager

    def reset_context(self):
        manager = _AttributeManager(context=self.context)
        self.context = {}
        return manager
