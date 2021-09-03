# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from ..model import Model, fields
from trytond.cache import Cache
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['Timer']


class Timer(Model):
    "Timer"
    __name__ = "ir.timer"

    @classmethod
    def start_timer(cls):
        return 0

    @classmethod
    def end_timer(cls, dt):
        return 0

    @classmethod
    def check_time(cls, tm):
        return False

    @classmethod
    def store_call(self, user, pool, method_name, time=10):
        pass
