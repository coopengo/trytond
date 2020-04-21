# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.model import ModelSQL, fields
from trytond.pool import Pool


class TestNote(ModelSQL):
    'Test Note'
    __name__ = 'test.note'

    name = fields.Char("Name")


def register(module):
    Pool.register(
        TestNote,
        module=module, type_='model')
