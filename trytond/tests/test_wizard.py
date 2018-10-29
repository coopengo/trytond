# This file is part of Tryton.  The COPYRIGHT file at the top level of this
# repository contains the full copyright notices and license terms.
import unittest
from trytond.tests.test_tryton import activate_module, with_transaction
from trytond.transaction import Transaction
from trytond.pool import Pool


class WizardTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        activate_module('tests')

    @with_transaction()
    def test_create(self):
        'Create Session Wizard'
        pool = Pool()
        Wizard = pool.get('test.test_wizard', type='wizard')

        session_id, start_state, end_state = Wizard.create()
        self.assertEqual(start_state, 'start')
        self.assertEqual(end_state, 'end')
        self.assertTrue(session_id)

    @with_transaction()
    def test_delete(self):
        'Delete Session Wizard'
        pool = Pool()
        Wizard = pool.get('test.test_wizard', type='wizard')

        session_id, _, _ = Wizard.create()
        Wizard.delete(session_id)

    @with_transaction()
    def test_session(self):
        'Session Wizard'
        pool = Pool()
        Wizard = pool.get('test.test_wizard', type='wizard')
        Session = pool.get('ir.session.wizard')
        Group = pool.get('res.group')
        transaction = Transaction()

        session_id, = Session.create([{}])
        session = Wizard(session_id)
        self.assertEqual(session.start.id, None)
        self.assertRaises(AttributeError, getattr, session.start, 'name')
        self.assertEqual(hasattr(session.start, 'name'), False)
        session.start.name = 'Test'
        self.assertRaises(AttributeError, getattr, session.start, 'user')
        self.assertEqual(hasattr(session.start, 'user'), False)
        session.start.user = transaction.user
        group_a, = Group.create([{
                    'name': 'Group A',
                    }])
        group_b, = Group.create([{
                    'name': 'Group B',
                    }])
        session.start.groups = [
            group_a,
            group_b,
            ]
        session._save()
        session = Wizard(session_id)
        self.assertEqual(session.start.id, None)
        self.assertEqual(session.start.name, 'Test')
        self.assertEqual(session.start.user.id, transaction.user)
        self.assertEqual(session.start.user.login, 'admin')
        group_a, group_b = session.start.groups
        self.assertEqual(group_a.name, 'Group A')
        self.assertEqual(group_b.name, 'Group B')

    @with_transaction()
    def test_execute(self):
        'Execute Wizard'
        pool = Pool()
        Wizard = pool.get('test.test_wizard', type='wizard')

        session_id, start_state, end_state = Wizard.create()
        result = Wizard.execute(session_id, {}, start_state)
        self.assertEqual(list(result.keys()), ['view'])
        self.assertEqual(result['view']['defaults'], {
                'name': 'Test wizard',
                })
        self.assertEqual(result['view']['buttons'], [
                {
                    'state': 'end',
                    'states': '{}',
                    'icon': 'tryton-cancel',
                    'default': False,
                    'string': 'Cancel',
                    },
                {
                    'state': 'next_',
                    'states': '{}',
                    'icon': 'tryton-next',
                    'default': True,
                    'string': 'Next',
                    },
                ])
        result = Wizard.execute(session_id, {
                start_state: {
                    'name': 'Test Update',
                    }}, 'next_')
        self.assertEqual(len(result['actions']), 1)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(WizardTestCase)
