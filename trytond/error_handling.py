# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys

from werkzeug.exceptions import Forbidden

from trytond.tools import resolve
from trytond.config import config
from trytond.exceptions import UserError, UserWarning, ConcurrencyException

ErrorHandlingClass = None


class HandledError(UserError):
    '''
    A UserError that wraps a technical error, so that:

        - It does not "frighten" the user
        - It avoids leaking technical informations
    '''
    __slots__ = ('event_id', 'original_error')

    def __init__(self, message, error_id):
        message = message.format(error_id)
        super().__init__(message)
        self.error_id = error_id
        self.original_error = sys.exc_info()


class ErrorHandler(object):
    '''
    Base class for error handling class.

    Provides the main entry point for handling error.
    '''
    _message = '{}'

    @staticmethod
    def handle_exception(error, reraise=True):
        '''
        Exception Handling method.

        If reraise is True, a HandledError will be raised to communicate with
        the end user, else the error will be returned so the caller can do
        something with it.
        '''
        set_handling_class()
        if ErrorHandlingClass is None:
            raise
        error_id = ErrorHandlingClass.do_handle_exception(error)
        wrapped_error = HandledError(ErrorHandlingClass._message, error_id)
        if reraise:
            raise wrapped_error
        return wrapped_error

    @classmethod
    def do_handle_exception(e):
        '''
        The actual error handling code, that must be implemented in subclasses.

        It is expected to return some sort of identifier that a user can then
        communicate to the maintainers
        '''
        raise NotImplementedError


def error_wrap(func):
    '''
    A decorator that can be placed on a function to plug raised errors on the
    handler
    '''
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (UserError, UserWarning, ConcurrencyException, Forbidden):
            # Those errors are supposed to make their way to the end user
            raise
        except Exception as e:
            ErrorHandler.handle_exception(e)
    return wrap


def set_handling_class():
    global ErrorHandlingClass
    if ErrorHandlingClass is not None:
        return

    if config.get('admin', 'error_handling_class'):
        ErrorHandlingClass = resolve(config.get('admin', 'error_handling_class'))
        assert issubclass(ErrorHandlingClass, ErrorHandler)
    else:
        ErrorHandlingClass = None
