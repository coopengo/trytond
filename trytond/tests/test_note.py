# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.tests.test_tryton import activate_module, with_transaction


class NoteTestCase(unittest.TestCase):
    "Test Note"

    @classmethod
    def setUpClass(cls):
        activate_module('tests')

    @with_transaction()
    def test_note_write(self):
        "Test note write behaviour"
        pool = Pool()
        Note = pool.get('ir.note')
        TestNote = pool.get('test.note')
        User = pool.get('res.user')

        user = User(login='test')
        user.save()
        record = TestNote()
        record.save()
        note = Note(resource=record, message="Message")
        note.save()
        write_date = note.write_date

        with Transaction().set_user(user.id):
            user_note = Note(note.id)
            user_note.unread = False
            user_note.save()

        note = Note(note.id)
        self.assertEqual(user_note.write_date, write_date)


def suite():
    suite_ = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite_.addTests(loader.loadTestsFromTestCase(NoteTestCase))
    return suite_
