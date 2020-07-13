# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.tests.test_tryton import activate_module, with_transaction


class ResourceTestCase(unittest.TestCase):
    "Test Resource"

    @classmethod
    def setUpClass(cls):
        activate_module('tests')

    @with_transaction()
    def test_resources_copied(self):
        "Test resources are copied"
        pool = Pool()
        Resource = pool.get('test.resource')
        Other = pool.get('test.resource.other')
        Note = pool.get('ir.note')

        record = Resource()
        record.save()
        note = Note(resource=record, copy_to_resources=[Other.__name__])
        note.save()
        other = Other()
        other.save()
        copies = record.copy_resources_to(other)

        other_notes = Note.search([('resource', '=', str(other))])
        self.assertTrue(other_notes)
        self.assertEqual(len(other_notes), 1)
        self.assertEqual(other_notes, copies)

    @with_transaction()
    def test_resources_not_copied(self):
        "Test resources are not copied"
        pool = Pool()
        Resource = pool.get('test.resource')
        Other = pool.get('test.resource.other')
        Note = pool.get('ir.note')

        record = Resource()
        record.save()
        note = Note(resource=record)
        note.save()
        other = Other()
        other.save()
        copies = record.copy_resources_to(other)

        other_notes = Note.search([('resource', '=', str(other))])
        self.assertFalse(other_notes)
        self.assertFalse(copies)

    @with_transaction()
    def test_note_write(self):
        "Test note write behaviour"
        pool = Pool()
        Note = pool.get('ir.note')
        Resource = pool.get('test.resource')
        User = pool.get('res.user')

        user = User(login='test')
        user.save()
        record = Resource()
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
    return unittest.TestLoader().loadTestsFromTestCase(ResourceTestCase)
