# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from dateutil.relativedelta import relativedelta
import datetime
import unittest

from trytond.pool import Pool
from trytond.transaction import Transaction
from .test_tryton import ModuleTestCase, with_transaction


class IrTestCase(ModuleTestCase):
    'Test ir module'
    module = 'ir'

    @with_transaction()
    def test_sequence_substitutions(self):
        'Test Sequence Substitutions'
        pool = Pool()
        Sequence = pool.get('ir.sequence')
        SequenceType = pool.get('ir.sequence.type')
        Date = pool.get('ir.date')
        try:
            Group = pool.get('res.group')
            groups = Group.search([])
        except KeyError:
            groups = []

        sequence_type = SequenceType(name='Test', code='test', groups=groups)
        sequence_type.save()
        sequence = Sequence(name='Test Sequence', code='test')
        sequence.save()
        self.assertEqual(Sequence.get_id(sequence.id), '1')
        today = Date.today()
        sequence.prefix = '${year}'
        sequence.save()
        self.assertEqual(Sequence.get_id(sequence.id),
            '%s2' % str(today.year))
        next_year = today + relativedelta(years=1)
        with Transaction().set_context(date=next_year):
            self.assertEqual(Sequence.get_id(sequence.id),
                '%s3' % str(next_year.year))

    @with_transaction()
    def test_global_search(self):
        'Test Global Search'
        pool = Pool()
        Model = pool.get('ir.model')
        Model.global_search('User', 10)

    @with_transaction()
    def test_lang_strftime(self):
        "Test Lang.strftime"
        pool = Pool()
        Lang = pool.get('ir.lang')
        test_data = [
            ((2016, 8, 3), 'en', '%d %B %Y', "03 August 2016"),
            ((2016, 8, 3), 'fr', '%d %B %Y', "03 ao\xfbt 2016"),
            ((2016, 8, 3), 'fr', '%d %B %Y', "03 ao\xfbt 2016"),
            ]
        for date, code, format_, result in test_data:
            lang = Lang.get(code)
            self.assertEqual(
                lang.strftime(datetime.date(*date), format_),
                result)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(IrTestCase)
