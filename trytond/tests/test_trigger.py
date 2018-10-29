# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import time
import datetime
from itertools import combinations

from trytond.tests.test_tryton import activate_module, with_transaction
from trytond.tests.trigger import TRIGGER_LOGS
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond.exceptions import UserError
from trytond.pyson import PYSONEncoder, Eval


class TriggerTestCase(unittest.TestCase):
    'Test Trigger'

    @classmethod
    def setUpClass(cls):
        activate_module('tests')

    @with_transaction()
    def test_constraints(self):
        'Test constraints'
        pool = Pool()
        Model = pool.get('ir.model')
        Trigger = pool.get('ir.trigger')
        transaction = Transaction()

        model, = Model.search([
                ('model', '=', 'test.triggered'),
                ])
        action_model, = Model.search([
                ('model', '=', 'test.trigger_action'),
                ])

        values = {
            'name': 'Test',
            'model': model.id,
            'on_time': True,
            'condition': 'true',
            'action_model': action_model.id,
            'action_function': 'test',
            }
        self.assertTrue(Trigger.create([values]))

        transaction.rollback()

        # on_exclusive
        for i in range(1, 4):
            for combination in combinations(
                    ['create', 'write', 'delete'], i):
                combination_values = values.copy()
                for mode in combination:
                    combination_values['on_%s' % mode] = True
                self.assertRaises(UserError, Trigger.create,
                    [combination_values])
                transaction.rollback()

        # check_condition
        condition_values = values.copy()
        condition_values['condition'] = '='
        self.assertRaises(UserError, Trigger.create,
            [condition_values])
        transaction.rollback()

        # Restart the cache on the get_triggers method of ir.trigger
        Trigger._get_triggers_cache.clear()

    @with_transaction()
    def test_on_create(self):
        'Test on_create'
        pool = Pool()
        Model = pool.get('ir.model')
        Trigger = pool.get('ir.trigger')
        Triggered = pool.get('test.triggered')

        model, = Model.search([
                ('model', '=', 'test.triggered'),
                ])
        action_model, = Model.search([
                ('model', '=', 'test.trigger_action'),
                ])

        trigger, = Trigger.create([{
                    'name': 'Test',
                    'model': model.id,
                    'on_create': True,
                    'condition': 'true',
                    'action_model': action_model.id,
                    'action_function': 'trigger',
                    }])

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])

        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Trigger with condition
        condition = PYSONEncoder().encode(
            Eval('self', {}).get('name') == 'Bar')
        Trigger.write([trigger], {
                'condition': condition,
                })

        # Matching condition
        triggered, = Triggered.create([{
                    'name': 'Bar',
                    }])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Non matching condition
        triggered, = Triggered.create([{
                    'name': 'Foo',
                    }])
        self.assertEqual(TRIGGER_LOGS, [])

        # With limit number
        Trigger.write([trigger], {
                'condition': 'true',
                'limit_number': 1,
                })
        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # With minimum delay
        Trigger.write([trigger], {
                'limit_number': 0,
                'minimum_time_delay': datetime.timedelta(hours=1),
                })
        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Restart the cache on the get_triggers method of ir.trigger
        Trigger._get_triggers_cache.clear()

    @with_transaction()
    def test0030on_write(self):
        'Test on_write'
        pool = Pool()
        Model = pool.get('ir.model')
        Trigger = pool.get('ir.trigger')
        Triggered = pool.get('test.triggered')

        model, = Model.search([
                ('model', '=', 'test.triggered'),
                ])
        action_model, = Model.search([
                ('model', '=', 'test.trigger_action'),
                ])

        trigger, = Trigger.create([{
                    'name': 'Test',
                    'model': model.id,
                    'on_write': True,
                    'condition': 'true',
                    'action_model': action_model.id,
                    'action_function': 'trigger',
                    }])

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])

        Triggered.write([triggered], {
                'name': 'Foo',
                })
        self.assertEqual(TRIGGER_LOGS, [])

        # Trigger with condition
        condition = PYSONEncoder().encode(
            Eval('self', {}).get('name') == 'Bar')
        Trigger.write([trigger], {
                'condition': condition,
                })

        # Matching condition
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # No change in condition
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        self.assertEqual(TRIGGER_LOGS, [])

        # Different change in condition
        Triggered.write([triggered], {
                'name': 'Foo',
                })
        self.assertEqual(TRIGGER_LOGS, [])

        # With limit number
        condition = PYSONEncoder().encode(
            Eval('self', {}).get('name') == 'Bar')
        Trigger.write([trigger], {
                'condition': condition,
                'limit_number': 1,
                })
        triggered, = Triggered.create([{
                    'name': 'Foo',
                    }])
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        Triggered.write([triggered], {
                'name': 'Foo',
                })
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # With minimum delay
        Trigger.write([trigger], {
                'limit_number': 0,
                'minimum_time_delay': datetime.timedelta.max,
                })
        triggered, = Triggered.create([{
                    'name': 'Foo',
                    }])
        for name in ('Bar', 'Foo', 'Bar'):
            Triggered.write([triggered], {
                    'name': name,
                    })
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        Trigger.write([trigger], {
                'minimum_time_delay': datetime.timedelta(seconds=1),
                })
        triggered, = Triggered.create([{
                    'name': 'Foo',
                    }])
        for name in ('Bar', 'Foo'):
            Triggered.write([triggered], {
                    'name': name,
                    })
        time.sleep(1.2)
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        self.assertEqual(TRIGGER_LOGS,
            [([triggered], trigger), ([triggered], trigger)])
        TRIGGER_LOGS.pop()
        TRIGGER_LOGS.pop()

        # Restart the cache on the get_triggers method of ir.trigger
        Trigger._get_triggers_cache.clear()

    @with_transaction()
    def test0040on_delete(self):
        'Test on_delete'
        pool = Pool()
        Model = pool.get('ir.model')
        Trigger = pool.get('ir.trigger')
        Triggered = pool.get('test.triggered')
        TriggerLog = pool.get('ir.trigger.log')

        model, = Model.search([
                ('model', '=', 'test.triggered'),
                ])
        action_model, = Model.search([
                ('model', '=', 'test.trigger_action'),
                ])

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])

        trigger, = Trigger.create([{
                    'name': 'Test',
                    'model': model.id,
                    'on_delete': True,
                    'condition': 'true',
                    'action_model': action_model.id,
                    'action_function': 'trigger',
                    }])

        Triggered.delete([triggered])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()
        Transaction().delete = {}

        # Trigger with condition
        condition = PYSONEncoder().encode(
            Eval('self', {}).get('name') == 'Bar')
        Trigger.write([trigger], {
                'condition': condition,
                })

        triggered, = Triggered.create([{
                    'name': 'Bar',
                    }])

        # Matching condition
        Triggered.delete([triggered])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()
        Transaction().delete = {}

        triggered, = Triggered.create([{
                    'name': 'Foo',
                    }])

        # Non matching condition
        Triggered.delete([triggered])
        self.assertEqual(TRIGGER_LOGS, [])
        Transaction().delete = {}

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])

        # With limit number
        Trigger.write([trigger], {
                'condition': 'true',
                'limit_number': 1,
                })
        Triggered.delete([triggered])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()
        Transaction().delete = {}
        # Delete trigger logs because SQLite reuse the same triggered_id
        TriggerLog.delete(TriggerLog.search([
                    ('trigger', '=', trigger.id),
                    ]))

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])

        # With minimum delay
        Trigger.write([trigger], {
                'limit_number': 0,
                'minimum_time_delay': datetime.timedelta(hours=1),
                })
        Triggered.delete([triggered])
        self.assertEqual(TRIGGER_LOGS, [([triggered], trigger)])
        TRIGGER_LOGS.pop()
        Transaction().delete = {}

        # Restart the cache on the get_triggers method of ir.trigger
        Trigger._get_triggers_cache.clear()

    @with_transaction()
    def test_on_time(self):
        'Test on_time'
        pool = Pool()
        Model = pool.get('ir.model')
        Trigger = pool.get('ir.trigger')
        Triggered = pool.get('test.triggered')
        TriggerLog = pool.get('ir.trigger.log')

        model, = Model.search([
                ('model', '=', 'test.triggered'),
                ])
        action_model, = Model.search([
                ('model', '=', 'test.trigger_action'),
                ])

        trigger, = Trigger.create([{
                    'name': 'Test',
                    'model': model.id,
                    'on_time': True,
                    'condition': 'true',
                    'action_model': action_model.id,
                    'action_function': 'trigger',
                    }])

        triggered, = Triggered.create([{
                    'name': 'Test',
                    }])
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Trigger with condition
        condition = PYSONEncoder().encode(
            Eval('self', {}).get('name') == 'Bar')
        Trigger.write([trigger], {
                'condition': condition,
                })

        # Matching condition
        Triggered.write([triggered], {
                'name': 'Bar',
                })
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Non matching condition
        Triggered.write([triggered], {
                'name': 'Foo',
                })
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [])

        # With limit number
        Trigger.write([trigger], {
                'condition': 'true',
                'limit_number': 1,
                })
        Trigger.trigger_time()
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [([triggered], trigger)])
        TRIGGER_LOGS.pop()

        # Delete trigger logs of limit number test
        TriggerLog.delete(TriggerLog.search([
                    ('trigger', '=', trigger.id),
                    ]))

        # With minimum delay
        Trigger.write([trigger], {
                'limit_number': 0,
                'minimum_time_delay': datetime.timedelta.max,
                })
        Trigger.trigger_time()
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [([triggered], trigger)])
        TRIGGER_LOGS.pop()
        Transaction().delete = {}

        # Delete trigger logs of previous minimum delay test
        TriggerLog.delete(TriggerLog.search([
                    ('trigger', '=', trigger.id),
                    ]))

        Trigger.write([trigger], {
                'minimum_time_delay': datetime.timedelta(seconds=1),
                })
        Trigger.trigger_time()
        time.sleep(1.2)
        Trigger.trigger_time()
        self.assertTrue(TRIGGER_LOGS == [([triggered], trigger),
                ([triggered], trigger)])
        TRIGGER_LOGS.pop()
        TRIGGER_LOGS.pop()
        Transaction().delete = {}

        # Restart the cache on the get_triggers method of ir.trigger
        Trigger._get_triggers_cache.clear()


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(TriggerTestCase)
