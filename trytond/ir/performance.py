# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

from ..model import ModelSQL, ModelView, fields
from trytond.cache import Cache
from trytond.pool import Pool
from trytond.transaction import Transaction

__all__ = ['Timer']


class Timer(ModelSQL, ModelView):
    "Timer"
    __name__ = "ir.timer"

    # _message_cache = Cache('ir.message', size_limit=10240, context=False)
    # text = fields.Text("Text", required=True, translate=True)
    # def __init__(self):
    #     self.dt = None

    @classmethod
    def start_timer(self):
        print('début chrono')

    @classmethod
    def end_timer(self):
        print('end chrono')

    @classmethod
    def check_time(self, tm, limit):
        print('time query')

    @classmethod
    def store_call(self, user, session, method_name, date, time=10):
        print('store call')
