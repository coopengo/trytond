# -*- coding: utf-8 -*-
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import sys
try:
    import cdecimal
    if 'decimal' not in sys.modules:
        sys.modules['decimal'] = cdecimal
except ImportError:
    import decimal
    sys.modules['cdecimal'] = decimal
import unittest
import datetime
import shutil
import tempfile

from decimal import Decimal
from trytond.tests.test_tryton import activate_module, with_transaction
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.model import fields
from trytond.pool import Pool
from trytond.config import config
from trytond import backend


class FieldsTestCase(unittest.TestCase):
    'Test Fields'

    @classmethod
    def setUpClass(cls):
        activate_module('tests')

    def setUp(self):
        path = config.get('database', 'path')
        dtemp = tempfile.mkdtemp()
        config.set('database', 'path', dtemp)
        self.addCleanup(config.set, 'database', 'path', path)
        self.addCleanup(shutil.rmtree, dtemp)

    @with_transaction()
    def test_boolean(self):
        'Test Boolean'
        pool = Pool()
        Boolean = pool.get('test.boolean')
        BooleanDefault = pool.get('test.boolean_default')

        boolean1, = Boolean.create([{
                    'boolean': True,
                    }])
        self.assert_(boolean1)
        self.assertEqual(boolean1.boolean, True)

        booleans = Boolean.search([
                ('boolean', '=', True),
                ])
        self.assertEqual(booleans, [boolean1])

        booleans = Boolean.search([
                ('boolean', '!=', True),
                ])
        self.assertEqual(booleans, [])

        booleans = Boolean.search([
                ('boolean', 'in', [True]),
                ])
        self.assertEqual(booleans, [boolean1])

        booleans = Boolean.search([
                ('boolean', 'in', [False]),
                ])
        self.assertEqual(booleans, [])

        booleans = Boolean.search([
                ('boolean', 'not in', [True]),
                ])
        self.assertEqual(booleans, [])

        booleans = Boolean.search([
                ('boolean', 'not in', [False]),
                ])
        self.assertEqual(booleans, [boolean1])

        boolean2, = Boolean.create([{
                    'boolean': False,
                    }])
        self.assert_(boolean2)
        self.assertEqual(boolean2.boolean, False)

        booleans = Boolean.search([
                ('boolean', '=', False),
                ])
        self.assertEqual(booleans, [boolean2])

        booleans = Boolean.search([
                ('boolean', 'in', [True, False]),
                ])
        self.assertEqual(booleans, [boolean1, boolean2])

        booleans = Boolean.search([
                ('boolean', 'not in', [True, False]),
                ])
        self.assertEqual(booleans, [])

        boolean3, = Boolean.create([{}])
        self.assert_(boolean3)
        self.assertEqual(boolean3.boolean, False)

        # Test search with NULL value
        boolean4, = Boolean.create([{
                    'boolean': None,
                    }])
        self.assert_(boolean4)

        booleans = Boolean.search([
                ('boolean', '=', False),
                ])
        self.assertEqual(booleans,
            [boolean2, boolean3, boolean4])

        booleans = Boolean.search([
                ('boolean', '!=', False),
                ])
        self.assertEqual(booleans, [boolean1])

        boolean4, = BooleanDefault.create([{}])
        self.assert_(boolean4)
        self.assertTrue(boolean4.boolean)

        Boolean.write([boolean1], {
                'boolean': False,
                })
        self.assertEqual(boolean1.boolean, False)

        Boolean.write([boolean2], {
                'boolean': True,
                })
        self.assertEqual(boolean2.boolean, True)

    @with_transaction()
    def test_integer(self):
        'Test Integer'
        pool = Pool()
        Integer = pool.get('test.integer')
        IntegerDefault = pool.get('test.integer_default')
        IntegerRequired = pool.get('test.integer_required')
        transaction = Transaction()

        integer1, = Integer.create([{
                    'integer': 1,
                    }])
        self.assert_(integer1)
        self.assertEqual(integer1.integer, 1)

        integers = Integer.search([
                ('integer', '=', 1),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '=', 0),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '!=', 1),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '!=', 0),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', 'in', [1]),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', 'in', [0]),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', 'in', []),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', 'not in', [1]),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', 'not in', [0]),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', 'not in', []),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '<', 5),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '<', -5),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '<', 1),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '<=', 5),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '<=', -5),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '<=', 1),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '>', 5),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '>', -5),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '>', 1),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '>=', 5),
                ])
        self.assertEqual(integers, [])

        integers = Integer.search([
                ('integer', '>=', -5),
                ])
        self.assertEqual(integers, [integer1])

        integers = Integer.search([
                ('integer', '>=', 1),
                ])
        self.assertEqual(integers, [integer1])

        integer2, = Integer.create([{
                    'integer': 0,
                    }])
        self.assert_(integer2)
        self.assertEqual(integer2.integer, 0)

        integers = Integer.search([
                ('integer', '=', 0),
                ])
        self.assertEqual(integers, [integer2])

        integers = Integer.search([
                ('integer', 'in', [0, 1]),
                ])
        self.assertEqual(integers, [integer1, integer2])

        integers = Integer.search([
                ('integer', 'not in', [0, 1]),
                ])
        self.assertEqual(integers, [])

        integer3, = Integer.create([{}])
        self.assert_(integer3)
        self.assertEqual(integer3.integer, None)

        integer4, = IntegerDefault.create([{}])
        self.assert_(integer4)
        self.assertEqual(integer4.integer, 5)

        Integer.write([integer1], {
                'integer': 0,
                })
        self.assertEqual(integer1.integer, 0)

        Integer.write([integer2], {
                'integer': 1,
                })
        self.assertEqual(integer2.integer, 1)

        self.assertRaises(Exception, Integer.create, [{
                    'integer': 'test',
                    }])

        self.assertRaises(Exception, Integer.write, [integer1], {
                'integer': 'test',
                })

        # We should catch UserError but mysql does not raise an
        # IntegrityError but an OperationalError
        self.assertRaises(Exception, IntegerRequired.create, [{}])
        transaction.rollback()

        integer5, = IntegerRequired.create([{
                    'integer': 0,
                    }])
        self.assert_(integer5)
        self.assertEqual(integer5.integer, 0)

        transaction.rollback()

    @with_transaction()
    def test_integer_with_domain(self):
        'Test Integer with domain'
        pool = Pool()
        IntegerDomain = pool.get('test.integer_domain')
        IntegerDomain.create([{
                    'integer': 100,
                    }])
        self.assertRaises(UserError, IntegerDomain.create, [{
                    'integer': 10,
                    }])

    @with_transaction()
    def test_float(self):
        'Test Float'
        pool = Pool()
        Float = pool.get('test.float')
        FloatDefault = pool.get('test.float_default')
        FloatRequired = pool.get('test.float_required')
        FloatDigits = pool.get('test.float_digits')
        transaction = Transaction()

        float1, = Float.create([{
                    'float': 1.1,
                    }])
        self.assert_(float1)
        self.assertEqual(float1.float, 1.1)

        floats = Float.search([
                ('float', '=', 1.1),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '=', 0),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '!=', 1.1),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '!=', 0),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', 'in', [1.1]),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', 'in', [0]),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', 'in', []),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', 'not in', [1.1]),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', 'not in', [0]),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', 'not in', []),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '<', 5),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '<', -5),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '<', 1.1),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '<=', 5),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '<=', -5),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '<=', 1.1),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '>', 5),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '>', -5),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '>', 1.1),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '>=', 5),
                ])
        self.assertEqual(floats, [])

        floats = Float.search([
                ('float', '>=', -5),
                ])
        self.assertEqual(floats, [float1])

        floats = Float.search([
                ('float', '>=', 1.1),
                ])
        self.assertEqual(floats, [float1])

        float2, = Float.create([{
                    'float': 0,
                    }])
        self.assert_(float2)
        self.assertEqual(float2.float, 0)

        floats = Float.search([
                ('float', '=', 0),
                ])
        self.assertEqual(floats, [float2])

        floats = Float.search([
                ('float', 'in', [0, 1.1]),
                ])
        self.assertEqual(floats, [float1, float2])

        floats = Float.search([
                ('float', 'not in', [0, 1.1]),
                ])
        self.assertEqual(floats, [])

        float3, = Float.create([{}])
        self.assert_(float3)
        self.assertEqual(float3.float, None)

        float4, = FloatDefault.create([{}])
        self.assert_(float4)
        self.assertEqual(float4.float, 5.5)

        Float.write([float1], {
                'float': 0,
                })
        self.assertEqual(float1.float, 0)

        Float.write([float2], {
                'float': 1.1,
                })
        self.assertEqual(float2.float, 1.1)

        self.assertRaises(Exception, Float.create, [{
                    'float': 'test',
                    }])

        self.assertRaises(Exception, Float.write, [float1], {
                'float': 'test',
                })

        self.assertRaises(UserError, FloatRequired.create, [{}])
        transaction.rollback()

        float5, = FloatRequired.create([{
                    'float': 0.0,
                    }])
        self.assertEqual(float5.float, 0.0)

        float6, = FloatDigits.create([{
                    'digits': 1,
                    'float': 1.1,
                    }])
        self.assert_(float6)

        self.assertRaises(UserError, FloatDigits.create, [{
                    'digits': 1,
                    'float': 1.11,
                    }])

        self.assertRaises(UserError, FloatDigits.write,
            [float6], {
                'float': 1.11,
                })

        self.assertRaises(UserError, FloatDigits.write,
            [float6], {
                'digits': 0,
                })

        float7, = Float.create([{
                    'float': 0.123456789012345,
                    }])
        self.assertEqual(float7.float, 0.123456789012345)

    @with_transaction()
    def test_float_digits_none(self):
        pool = Pool()
        FloatDigits = pool.get('test.float_digits')
        record, = FloatDigits.create([{
                    'float': 0.123456789012345,
                    'digits': None,
                    }])
        self.assertEqual(record.float, 0.123456789012345)

    @with_transaction()
    def test_float_search_none(self):
        'Test float search with None'
        pool = Pool()
        Float = pool.get('test.float')

        float_none, float0, float1 = Float.create([{
                    'float': None,
                    }, {
                    'float': 0,
                    }, {
                    'float': 1,
                    }])
        self.assertEqual([float_none], Float.search([
                    ('float', '=', None),
                    ]))
        self.assertEqual([float0], Float.search([
                    ('float', '=', 0),
                    ]))
        self.assertEqual([float1], Float.search([
                    ('float', '>', 0),
                    ]))

        self.assertEqual([float0, float1], Float.search([
                    ('float', '!=', None),
                    ]))
        self.assertEqual([float1], Float.search([
                    ('float', '!=', 0),
                    ]))
        self.assertEqual([float0], Float.search([
                    ('float', '<', 1),
                    ]))

        self.assertEqual([float_none, float1], Float.search([
                    'OR',
                    ('float', '>', 0),
                    ('float', '=', None),
                    ]))

    @with_transaction()
    def test_numeric(self):
        'Test Numeric'
        pool = Pool()
        Numeric = pool.get('test.numeric')
        NumericDefault = pool.get('test.numeric_default')
        NumericRequired = pool.get('test.numeric_required')
        NumericDigits = pool.get('test.numeric_digits')
        transaction = Transaction()

        numeric1, = Numeric.create([{
                    'numeric': Decimal('1.1'),
                    }])
        self.assert_(numeric1)
        self.assertEqual(numeric1.numeric, Decimal('1.1'))

        numerics = Numeric.search([
                ('numeric', '=', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '=', Decimal('0')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '!=', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '!=', Decimal('0')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', 'in', [Decimal('1.1')]),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', 'in', [Decimal('0')]),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', 'in', []),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', 'not in', [Decimal('1.1')]),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', 'not in', [Decimal('0')]),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', 'not in', []),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '<', Decimal('5')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '<', Decimal('-5')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '<', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '<=', Decimal('5')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '<=', Decimal('-5')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '<=', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '>', Decimal('5')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '>', Decimal('-5')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '>', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '>=', Decimal('5')),
                ])
        self.assertEqual(numerics, [])

        numerics = Numeric.search([
                ('numeric', '>=', Decimal('-5')),
                ])
        self.assertEqual(numerics, [numeric1])

        numerics = Numeric.search([
                ('numeric', '>=', Decimal('1.1')),
                ])
        self.assertEqual(numerics, [numeric1])

        numeric2, = Numeric.create([{
                    'numeric': Decimal('0'),
                    }])
        self.assert_(numeric2)
        self.assertEqual(numeric2.numeric, Decimal('0'))

        numerics = Numeric.search([
                ('numeric', '=', Decimal('0')),
                ])
        self.assertEqual(numerics, [numeric2])

        numerics = Numeric.search([
                ('numeric', 'in', [Decimal('0'), Decimal('1.1')]),
                ])
        self.assertEqual(numerics, [numeric1, numeric2])

        numerics = Numeric.search([
                ('numeric', 'not in', [Decimal('0'), Decimal('1.1')]),
                ])
        self.assertEqual(numerics, [])

        numeric3, = Numeric.create([{}])
        self.assert_(numeric3)
        self.assertEqual(numeric3.numeric, None)

        numeric4, = NumericDefault.create([{}])
        self.assert_(numeric4)
        self.assertEqual(numeric4.numeric, Decimal('5.5'))

        Numeric.write([numeric1], {
                'numeric': Decimal('0'),
                })
        self.assertEqual(numeric1.numeric, Decimal('0'))

        Numeric.write([numeric2], {
                'numeric': Decimal('1.1'),
                })
        self.assertEqual(numeric2.numeric, Decimal('1.1'))

        self.assertRaises(Exception, Numeric.create, [{
                    'numeric': 'test',
                    }])

        self.assertRaises(Exception, Numeric.write, [numeric1], {
                'numeric': 'test',
                })

        self.assertRaises(UserError, NumericRequired.create, [{}])
        transaction.rollback()

        numeric5, = NumericRequired.create([{
                'numeric': Decimal(0),
                }])
        self.assertEqual(numeric5.numeric, 0)

        numeric6, = NumericDigits.create([{
                    'digits': 1,
                    'numeric': Decimal('1.1'),
                    }])
        self.assert_(numeric6)

        self.assertRaises(UserError, NumericDigits.create, [{
                    'digits': 1,
                    'numeric': Decimal('1.11'),
                    }])

        self.assertRaises(UserError, NumericDigits.write,
            [numeric6], {
                'numeric': Decimal('1.11'),
                })

        self.assertRaises(UserError, NumericDigits.write,
            [numeric6], {
                'numeric': Decimal('0.10000000000000001'),
                })

        self.assertRaises(UserError, NumericDigits.write,
            [numeric6], {
                'digits': 0,
                })

        numeric7, = Numeric.create([{
                    'numeric': Decimal('0.1234567890123456789'),
                    }])
        self.assertEqual(numeric7.numeric,
            Decimal('0.1234567890123456789'))

    @with_transaction()
    def test_numeric_search_cast(self):
        'Test numeric search cast'
        pool = Pool()
        Numeric = pool.get('test.numeric')

        numeric1, numeric2 = Numeric.create([{
                    'numeric': Decimal('1.1'),
                    }, {
                    'numeric': Decimal('100.0'),
                    }])
        numerics = Numeric.search([
                ('numeric', '<', Decimal('5')),
                ])
        self.assertEqual(numerics, [numeric1])

    @with_transaction()
    def test_numeric_search_none(self):
        'Test numeric search with None'
        pool = Pool()
        Numeric = pool.get('test.numeric')

        numeric_none, numeric0, numeric1 = Numeric.create([{
                    'numeric': None,
                    }, {
                    'numeric': 0,
                    }, {
                    'numeric': 1,
                    }])
        self.assertEqual([numeric_none], Numeric.search([
                    ('numeric', '=', None),
                    ]))
        self.assertEqual([numeric0], Numeric.search([
                    ('numeric', '=', 0),
                    ]))
        self.assertEqual([numeric1], Numeric.search([
                    ('numeric', '>', 0),
                    ]))

        self.assertEqual([numeric0, numeric1], Numeric.search([
                    ('numeric', '!=', None),
                    ]))
        self.assertEqual([numeric1], Numeric.search([
                    ('numeric', '!=', 0),
                    ]))
        self.assertEqual([numeric0], Numeric.search([
                    ('numeric', '<', 1),
                    ]))

        self.assertEqual([numeric_none, numeric1], Numeric.search([
                    'OR',
                    ('numeric', '>', 0),
                    ('numeric', '=', None),
                    ]))

    @with_transaction()
    def test_char(self):
        'Test Char'
        pool = Pool()
        Char = pool.get('test.char')
        CharDefault = pool.get('test.char_default')
        CharRequired = pool.get('test.char_required')
        CharSize = pool.get('test.char_size')
        CharTranslate = pool.get('test.char_translate')
        transaction = Transaction()

        for char in (CharTranslate, Char):
            char1, = char.create([{
                        'char': 'Test',
                        }])
            self.assert_(char1)
            self.assertEqual(char1.char, 'Test')

            chars = char.search([
                    ('char', '=', 'Test'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', '=', 'Foo'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', '=', None),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', '!=', 'Test'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', '!=', 'Foo'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', '!=', None),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'in', ['Test']),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'in', ['Foo']),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'in', [None]),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'in', []),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not in', ['Test']),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not in', ['Foo']),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'not in', [None]),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'not in', []),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'like', 'Test'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'like', 'T%'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'like', 'Foo'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'like', 'F%'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'ilike', 'test'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'ilike', 't%'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'ilike', 'foo'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'ilike', 'f%'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not like', 'Test'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not like', 'T%'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not like', 'Foo'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'not like', 'F%'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'not ilike', 'test'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not ilike', 't%'),
                    ])
            self.assertEqual(chars, [])

            chars = char.search([
                    ('char', 'not ilike', 'foo'),
                    ])
            self.assertEqual(chars, [char1])

            chars = char.search([
                    ('char', 'not ilike', 'f%'),
                    ])
            self.assertEqual(chars, [char1])

            char2, = char.create([{
                        'char': None,
                        }])
            self.assert_(char2)
            self.assertEqual(char2.char, None)

            chars = char.search([
                    ('char', '=', None),
                    ])
            self.assertEqual(chars, [char2])

            chars = char.search([
                    ('char', 'in', [None, 'Test']),
                    ])
            self.assertEqual(chars, [char1, char2])

            chars = char.search([
                    ('char', 'not in', [None, 'Test']),
                    ])
            self.assertEqual(chars, [])

        char3, = Char.create([{}])
        self.assert_(char3)
        self.assertEqual(char3.char, None)

        char4, = CharDefault.create([{}])
        self.assert_(char4)
        self.assertEqual(char4.char, 'Test')

        Char.write([char1], {
                'char': None,
                })
        self.assertEqual(char1.char, None)

        Char.write([char2], {
                'char': 'Test',
                })
        self.assertEqual(char2.char, 'Test')

        self.assertRaises(UserError, CharRequired.create, [{}])
        transaction.rollback()

        self.assertRaises(UserError, CharRequired.create, [{
                'char': '',
                }])
        transaction.rollback()

        char5, = CharRequired.create([{
                    'char': 'Test',
                    }])
        self.assert_(char5)

        char6, = CharSize.create([{
                    'char': 'Test',
                    }])
        self.assert_(char6)

        self.assertRaises(Exception, CharSize.create, [{
                'char': 'foobar',
                }])

        self.assertRaises(Exception, CharSize.write, [char6], {
                'char': 'foobar',
                })
        transaction.rollback()

        char7, = Char.create([{
                    'char': u'é',
                    }])
        self.assert_(char7)
        self.assertEqual(char7.char, u'é')

        chars = Char.search([
                ('char', '=', u'é'),
                ])
        self.assertEqual(chars, [char7])

        Char.write([char7], {
                'char': 'é',
                })
        self.assertEqual(char7.char, u'é')

        chars = Char.search([
                ('char', '=', 'é'),
                ])
        self.assertEqual(chars, [char7])

    @with_transaction()
    def test_text(self):
        'Test Text'
        pool = Pool()
        Text = pool.get('test.text')
        TextDefault = pool.get('test.text_default')
        TextRequired = pool.get('test.text_required')
        TextSize = pool.get('test.text_size')
        TextTranslate = pool.get('test.text_translate')
        transaction = Transaction()

        for text in (TextTranslate, Text):
            text1, = text.create([{
                        'text': 'Test',
                        }])
            self.assert_(text1)
            self.assertEqual(text1.text, 'Test')

            texts = text.search([
                    ('text', '=', 'Test'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', '=', 'Foo'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', '=', None),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', '!=', 'Test'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', '!=', 'Foo'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', '!=', None),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'in', ['Test']),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'in', ['Foo']),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'in', [None]),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'in', []),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not in', ['Test']),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not in', ['Foo']),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'not in', [None]),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'not in', []),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'like', 'Test'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'like', 'T%'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'like', 'Foo'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'like', 'F%'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'ilike', 'test'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'ilike', 't%'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'ilike', 'foo'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'ilike', 'f%'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not like', 'Test'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not like', 'T%'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not like', 'Foo'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'not like', 'F%'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'not ilike', 'test'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not ilike', 't%'),
                    ])
            self.assertEqual(texts, [])

            texts = text.search([
                    ('text', 'not ilike', 'foo'),
                    ])
            self.assertEqual(texts, [text1])

            texts = text.search([
                    ('text', 'not ilike', 'f%'),
                    ])
            self.assertEqual(texts, [text1])

            text2, = text.create([{
                        'text': None,
                        }])
            self.assert_(text2)
            self.assertEqual(text2.text, None)

            texts = text.search([
                    ('text', '=', None),
                    ])
            self.assertEqual(texts, [text2])

            texts = text.search([
                    ('text', 'in', [None, 'Test']),
                    ])
            self.assertEqual(texts, [text1, text2])

            texts = text.search([
                    ('text', 'not in', [None, 'Test']),
                    ])
            self.assertEqual(texts, [])

        text3, = Text.create([{}])
        self.assert_(text3)
        self.assertEqual(text3.text, None)

        text4, = TextDefault.create([{}])
        self.assert_(text4)
        self.assertEqual(text4.text, 'Test')

        Text.write([text1], {
                'text': None,
                })
        self.assertEqual(text1.text, None)

        Text.write([text2], {
                'text': 'Test',
                })
        self.assertEqual(text2.text, 'Test')

        self.assertRaises(UserError, TextRequired.create, [{}])
        transaction.rollback()

        text5, = TextRequired.create([{
                    'text': 'Test',
                    }])
        self.assert_(text5)

        text6, = TextSize.create([{
                    'text': 'Test',
                    }])
        self.assert_(text6)

        self.assertRaises(UserError, TextSize.create, [{
                    'text': 'foobar',
                    }])

        self.assertRaises(UserError, TextSize.write, [text6], {
                'text': 'foobar',
                })

        text7, = Text.create([{
                    'text': 'Foo\nBar',
                    }])
        self.assert_(text7)

        text8, = Text.create([{
                    'text': u'é',
                    }])
        self.assert_(text8)
        self.assertEqual(text8.text, u'é')

        texts = Text.search([
                ('text', '=', u'é'),
                ])
        self.assertEqual(texts, [text8])

        Text.write([text8], {
                'text': 'é',
                })
        self.assertEqual(text8.text, u'é')

        texts = Text.search([
                ('text', '=', 'é'),
                ])
        self.assertEqual(texts, [text8])

    @with_transaction()
    def test_date(self):
        'Test Date'
        pool = Pool()
        Date = pool.get('test.date')
        DateDefault = pool.get('test.date_default')
        DateRequired = pool.get('test.date_required')
        transaction = Transaction()

        today = datetime.date(2009, 1, 1)
        tomorrow = today + datetime.timedelta(1)
        yesterday = today - datetime.timedelta(1)
        default_date = datetime.date(2000, 1, 1)

        date1, = Date.create([{
                    'date': today,
                    }])
        self.assert_(date1)
        self.assertEqual(date1.date, today)

        dates = Date.search([
                ('date', '=', today),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '=', tomorrow),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '=', None),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '!=', today),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '!=', tomorrow),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '!=', None),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', 'in', [today]),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', 'in', [tomorrow]),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', 'in', [None]),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', 'in', []),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', 'not in', [today]),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', 'not in', [tomorrow]),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', 'not in', [None]),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', 'not in', []),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '<', tomorrow),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '<', yesterday),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '<', today),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '<=', today),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '<=', yesterday),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '<=', tomorrow),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '>', tomorrow),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '>', yesterday),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '>', today),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '>=', tomorrow),
                ])
        self.assertEqual(dates, [])

        dates = Date.search([
                ('date', '>=', yesterday),
                ])
        self.assertEqual(dates, [date1])

        dates = Date.search([
                ('date', '>=', today),
                ])
        self.assertEqual(dates, [date1])

        date2, = Date.create([{
                    'date': yesterday,
                    }])
        self.assert_(date2)
        self.assertEqual(date2.date, yesterday)

        dates = Date.search([
                ('date', '=', yesterday),
                ])
        self.assertEqual(dates, [date2])

        dates = Date.search([
                ('date', 'in', [yesterday, today]),
                ])
        self.assertEqual(dates, [date1, date2])

        dates = Date.search([
                ('date', 'not in', [yesterday, today]),
                ])
        self.assertEqual(dates, [])

        date3, = Date.create([{}])
        self.assert_(date3)
        self.assertEqual(date3.date, None)

        date4, = DateDefault.create([{}])
        self.assert_(date4)
        self.assertEqual(date4.date, default_date)

        Date.write([date1], {
                'date': yesterday,
                })
        self.assertEqual(date1.date, yesterday)

        Date.write([date2], {
                'date': today,
                })
        self.assertEqual(date2.date, today)

        self.assertRaises(Exception, Date.create, [{
                    'date': 'test',
                    }])

        self.assertRaises(Exception, Date.write, [date1], {
                'date': 'test',
                })

        self.assertRaises(Exception, Date.create, [{
                    'date': 1,
                    }])

        self.assertRaises(Exception, Date.write, [date1], {
                'date': 1,
                })

        self.assertRaises(Exception, Date.create, [{
                    'date': datetime.datetime.now(),
                    }])

        self.assertRaises(Exception, Date.write, [date1], {
                'date': datetime.datetime.now(),
                })

        self.assertRaises(Exception, Date.create, [{
                    'date': '2009-13-01',
                    }])

        self.assertRaises(Exception, Date.write, [date1], {
                'date': '2009-02-29',
                })

        date5, = Date.create([{
                    'date': '2009-01-01',
                    }])
        self.assert_(date5)
        self.assertEqual(date5.date, datetime.date(2009, 1, 1))

        self.assertRaises(UserError, DateRequired.create, [{}])
        transaction.rollback()

        date6, = DateRequired.create([{
                    'date': today,
                    }])
        self.assert_(date6)

        date7, = Date.create([{
                    'date': None,
                    }])
        self.assert_(date7)

        date8, = Date.create([{
                    'date': None,
                    }])
        self.assert_(date8)

    @with_transaction()
    def test_datetime(self):
        'Test DateTime'
        pool = Pool()
        Datetime = pool.get('test.datetime')
        DatetimeDefault = pool.get('test.datetime_default')
        DatetimeRequired = pool.get('test.datetime_required')
        DatetimeFormat = pool.get('test.datetime_format')
        transaction = Transaction()

        today = datetime.datetime(2009, 1, 1, 12, 0, 0)
        tomorrow = today + datetime.timedelta(1)
        yesterday = today - datetime.timedelta(1)
        default_datetime = datetime.datetime(2000, 1, 1, 12, 0, 0)

        datetime1, = Datetime.create([{
                    'datetime': today,
                    }])
        self.assert_(datetime1)
        self.assertEqual(datetime1.datetime, today)

        datetimes = Datetime.search([
                ('datetime', '=', today),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '=', tomorrow),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '=', None),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '!=', today),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '!=', tomorrow),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '!=', None),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', 'in', [today]),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', 'in', [tomorrow]),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', 'in', [None]),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', 'in', []),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', 'not in', [today]),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', 'not in', [tomorrow]),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', 'not in', [None]),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', 'not in', []),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '<', tomorrow),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '<', yesterday),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '<', today),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '<=', today),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '<=', yesterday),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '<=', tomorrow),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '>', tomorrow),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '>', yesterday),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '>', today),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '>=', tomorrow),
                ])
        self.assertEqual(datetimes, [])

        datetimes = Datetime.search([
                ('datetime', '>=', yesterday),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetimes = Datetime.search([
                ('datetime', '>=', today),
                ])
        self.assertEqual(datetimes, [datetime1])

        datetime2, = Datetime.create([{
                    'datetime': yesterday,
                    }])
        self.assert_(datetime2)
        self.assertEqual(datetime2.datetime, yesterday)

        datetimes = Datetime.search([
                ('datetime', '=', yesterday),
                ])
        self.assertEqual(datetimes, [datetime2])

        datetimes = Datetime.search([
                ('datetime', 'in', [yesterday, today]),
                ])
        self.assertEqual(datetimes, [datetime1, datetime2])

        datetimes = Datetime.search([
                ('datetime', 'not in', [yesterday, today]),
                ])
        self.assertEqual(datetimes, [])

        datetime3, = Datetime.create([{}])
        self.assert_(datetime3)
        self.assertEqual(datetime3.datetime, None)

        datetime4, = DatetimeDefault.create([{}])
        self.assert_(datetime4)
        self.assertEqual(datetime4.datetime, default_datetime)

        Datetime.write([datetime1], {
                'datetime': yesterday,
                })
        self.assertEqual(datetime1.datetime, yesterday)

        Datetime.write([datetime2], {
                'datetime': today,
                })
        self.assertEqual(datetime2.datetime, today)

        self.assertRaises(Exception, Datetime.create, [{
                    'datetime': 'test',
                    }])

        self.assertRaises(Exception, Datetime.write, [datetime1],
            {
                'datetime': 'test',
                })

        self.assertRaises(Exception, Datetime.create, [{
                    'datetime': 1,
                    }])

        self.assertRaises(Exception, Datetime.write, [datetime1],
            {
                'datetime': 1,
                })

        self.assertRaises(Exception, Datetime.create, [{
                    'datetime': datetime.date.today(),
                    }])

        self.assertRaises(Exception, Datetime.write, [datetime1],
            {
                'datetime': datetime.date.today(),
                })

        self.assertRaises(Exception, Datetime.create, [{
                    'datetime': '2009-13-01 12:30:00',
                    }])

        self.assertRaises(Exception, Datetime.write, [datetime1],
            {
                'datetime': '2009-02-29 12:30:00',
                })

        self.assertRaises(Exception, Datetime.write, [datetime1],
            {
                'datetime': '2009-01-01 25:00:00',
                })

        datetime5, = Datetime.create([{
                'datetime': '2009-01-01 12:00:00',
                }])
        self.assert_(datetime5)
        self.assertEqual(datetime5.datetime,
            datetime.datetime(2009, 1, 1, 12, 0, 0))

        self.assertRaises(UserError, DatetimeRequired.create, [{}])
        transaction.rollback()

        datetime6, = DatetimeRequired.create([{
                    'datetime': today,
                    }])
        self.assert_(datetime6)

        datetime7, = Datetime.create([{
                    'datetime': None,
                    }])
        self.assert_(datetime7)

        datetime8, = Datetime.create([{
                    'datetime': None,
                    }])
        self.assert_(datetime8)

        datetime9, = Datetime.create([{
                    'datetime': today.replace(microsecond=1),
                    }])
        self.assert_(datetime9)
        self.assertEqual(datetime9.datetime, today)

        # Test format
        self.assert_(DatetimeFormat.create([{
                        'datetime': datetime.datetime(2009, 1, 1, 12, 30),
                        }]))
        self.assertRaises(UserError, DatetimeFormat.create, [{
                    'datetime': datetime.datetime(2009, 1, 1, 12, 30, 25),
                    }])

    @with_transaction()
    def test_time(self):
        'Test Time'
        pool = Pool()
        Time = pool.get('test.time')
        TimeDefault = pool.get('test.time_default')
        TimeRequired = pool.get('test.time_required')
        TimeFormat = pool.get('test.time_format')
        transaction = Transaction()

        pre_evening = datetime.time(16, 30)
        evening = datetime.time(18, 45, 3)
        night = datetime.time(20, 00)
        default_time = datetime.time(16, 30)

        time1, = Time.create([{
                    'time': evening,
                    }])
        self.assert_(time1)
        self.assertEqual(time1.time, evening)

        times = Time.search([
                ('time', '=', evening),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '=', night),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '=', None),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '!=', evening),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '!=', night),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '!=', None),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', 'in', [evening]),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', 'in', [night]),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', 'in', [None]),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', 'in', []),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', 'not in', [evening]),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', 'not in', [night]),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', 'not in', [None]),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', 'not in', []),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '<', night),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '<', pre_evening),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '<', evening),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '<=', evening),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '<=', pre_evening),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '<=', night),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '>', night),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '>', pre_evening),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '>', evening),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '>=', night),
                ])
        self.assertEqual(times, [])

        times = Time.search([
                ('time', '>=', pre_evening),
                ])
        self.assertEqual(times, [time1])

        times = Time.search([
                ('time', '>=', evening),
                ])
        self.assertEqual(times, [time1])

        time2, = Time.create([{
                    'time': pre_evening,
                    }])
        self.assert_(time2)
        self.assertEqual(time2.time, pre_evening)

        times = Time.search([
                ('time', '=', pre_evening),
                ])
        self.assertEqual(times, [time2])

        times = Time.search([
                ('time', 'in', [pre_evening, evening]),
                ])
        self.assertEqual(times, [time1, time2])

        times = Time.search([
                ('time', 'not in', [pre_evening, evening]),
                ])
        self.assertEqual(times, [])

        time3, = Time.create([{}])
        self.assert_(time3)
        self.assertEqual(time3.time, None)

        time4, = TimeDefault.create([{}])
        self.assert_(time4)
        self.assertEqual(time4.time, default_time)

        Time.write([time1], {
                'time': pre_evening,
                })
        self.assertEqual(time1.time, pre_evening)

        Time.write([time2], {
                'time': evening,
                })
        self.assertEqual(time2.time, evening)

        self.assertRaises(Exception, Time.create, [{
                    'time': 'test',
                    }])

        self.assertRaises(Exception, Time.write, [time1],
            {
                'time': 'test',
                })

        self.assertRaises(Exception, Time.create, [{
                'time': 1,
                }])

        self.assertRaises(Exception, Time.write, [time1],
            {
                'time': 1,
                })

        self.assertRaises(Exception, Time.write, [time1],
            {
                'time': '25:00:00',
                })

        time5, = Time.create([{
                    'time': '12:00:00',
                    }])
        self.assert_(time5)
        self.assertEqual(time5.time, datetime.time(12, 0))

        self.assertRaises(UserError, TimeRequired.create, [{}])
        transaction.rollback()

        time6, = TimeRequired.create([{
                    'time': evening,
                    }])
        self.assert_(time6)

        time7, = Time.create([{
                    'time': None,
                    }])
        self.assert_(time7)

        time9, = Time.create([{
                    'time': evening.replace(microsecond=1),
                    }])
        self.assert_(time9)
        self.assertEqual(time9.time, evening)

        # Test format
        self.assert_(TimeFormat.create([{
                    'time': datetime.time(12, 30),
                    }]))
        self.assertRaises(UserError, TimeFormat.create, [{
                'time': datetime.time(12, 30, 25),
                }])

    @with_transaction()
    def test_one2one(self):
        'Test One2One'
        pool = Pool()
        One2one = pool.get('test.one2one')
        One2oneTarget = pool.get('test.one2one.target')
        One2oneRequired = pool.get('test.one2one_required')
        One2oneDomain = pool.get('test.one2one_domain')
        transaction = Transaction()

        target1, = One2oneTarget.create([{
                    'name': 'target1',
                    }])
        one2one1, = One2one.create([{
                    'name': 'origin1',
                    'one2one': target1.id,
                    }])
        self.assert_(one2one1)
        self.assertEqual(one2one1.one2one, target1)

        self.assertEqual(One2one.read([one2one1.id],
                ['one2one.name'])[0]['one2one.name'], 'target1')

        one2ones = One2one.search([
                ('one2one', '=', 'target1'),
                ])
        self.assertEqual(one2ones, [one2one1])

        one2ones = One2one.search([
                ('one2one', '!=', 'target1'),
                ])
        self.assertEqual(one2ones, [])

        one2ones = One2one.search([
                ('one2one', 'in', [target1.id]),
                ])
        self.assertEqual(one2ones, [one2one1])

        one2ones = One2one.search([
                ('one2one', 'in', [0]),
                ])
        self.assertEqual(one2ones, [])

        one2ones = One2one.search([
                ('one2one', 'not in', [target1.id]),
                ])
        self.assertEqual(one2ones, [])

        one2ones = One2one.search([
                ('one2one', 'not in', [0]),
                ])
        self.assertEqual(one2ones, [one2one1])

        one2ones = One2one.search([
                ('one2one.name', '=', 'target1'),
                ])
        self.assertEqual(one2ones, [one2one1])

        one2ones = One2one.search([
                ('one2one.name', '!=', 'target1'),
                ])
        self.assertEqual(one2ones, [])

        one2one2, = One2one.create([{
                    'name': 'origin2',
                    }])
        self.assert_(one2one2)
        self.assertEqual(one2one2.one2one, None)

        one2ones = One2one.search([
                ('one2one', '=', None),
                ])
        self.assertEqual(one2ones, [one2one2])

        target2, = One2oneTarget.create([{
                    'name': 'target2',
                    }])
        One2one.write([one2one2], {
                'one2one': target2.id,
                })
        self.assertEqual(one2one2.one2one, target2)

        One2one.write([one2one2], {
                'one2one': None,
                })
        self.assertEqual(one2one2.one2one, None)

        self.assertRaises(UserError, One2one.create, [{
                    'name': 'one2one3',
                    'one2one': target1.id,
                    }])
        transaction.rollback()

        self.assertRaises(UserError, One2one.write, [one2one2], {
                'one2one': target1.id,
                })
        transaction.rollback()

        self.assertRaises(UserError, One2oneRequired.create, [{
                    'name': 'one2one3',
                    }])
        transaction.rollback()

        target3, = One2oneTarget.create([{
                    'name': 'target3',
                    }])

        one2one3, = One2oneRequired.create([{
                    'name': 'one2one3',
                    'one2one': target3.id,
                    }])
        self.assert_(one2one3)

        target4, = One2oneTarget.create([{
                    'name': 'target4',
                    }])
        self.assertRaises(UserError, One2oneDomain.create, [{
                    'name': 'one2one4',
                    'one2one': target4.id,
                    }])
        transaction.rollback()

        target5, = One2oneTarget.create([{
                    'name': 'domain',
                    }])
        one2one5, = One2oneDomain.create([{
                    'name': 'one2one5',
                    'one2one': target5.id,
                    }])
        targets = One2oneTarget.create([{
                    'name': 'multiple1',
                    }, {
                    'name': 'multiple2',
                    }])
        one2ones = One2one.create([{
                    'name': 'origin6',
                    'one2one': targets[0].id,
                    }, {
                    'name': 'origin7',
                    'one2one': targets[1].id,
                    }])
        for one2one, target in zip(one2ones, targets):
            self.assert_(one2one)
            self.assertEqual(one2one.one2one, target)

    @with_transaction()
    def test_one2many(self):
        'Test One2Many'
        pool = Pool()
        One2many = pool.get('test.one2many')
        One2manyTarget = pool.get('test.one2many.target')
        One2manyRequired = pool.get('test.one2many_required')
        One2manyReference = pool.get('test.one2many_reference')
        One2manyReferenceTarget = pool.get('test.one2many_reference.target')
        One2manySize = pool.get('test.one2many_size')
        One2manySizePyson = pool.get('test.one2many_size_pyson')
        transaction = Transaction()

        for one2many, one2many_target in (
                (One2many, One2manyTarget),
                (One2manyReference, One2manyReferenceTarget),
                ):
            one2many1, = one2many.create([{
                        'name': 'origin1',
                        'targets': [
                            ('create', [{
                                        'name': 'target1',
                                        }]),
                            ],
                        }])
            self.assert_(one2many1)

            self.assertEqual(len(one2many1.targets), 1)
            target1, = one2many1.targets

            # Try with target1 stored in cache
            target1 = one2many_target(target1.id)
            target1.origin
            one2many1 = one2many(one2many1)
            self.assertEqual(one2many1.targets, (target1,))

            one2manys = one2many.search([
                    ('targets', '=', 'target1'),
                    ])
            self.assertEqual(one2manys, [one2many1])

            one2manys = one2many.search([
                    ('targets', '!=', 'target1'),
                    ])
            self.assertEqual(one2manys, [])

            one2manys = one2many.search([
                    ('targets', 'in', [target1.id]),
                    ])
            self.assertEqual(one2manys, [one2many1])

            one2manys = one2many.search([
                    ('targets', 'in', [0]),
                    ])
            self.assertEqual(one2manys, [])

            one2manys = one2many.search([
                    ('targets', 'not in', (target1.id,)),
                    ])
            self.assertEqual(one2manys, [])

            one2manys = one2many.search([
                    ('targets', 'not in', [0]),
                    ])
            self.assertEqual(one2manys, [one2many1])

            one2manys = one2many.search([
                    ('targets.name', '=', 'target1'),
                    ])
            self.assertEqual(one2manys, [one2many1])

            one2manys = one2many.search([
                    ('targets.name', '!=', 'target1'),
                    ])
            self.assertEqual(one2manys, [])

            one2manys = one2many.search([
                    ('targets', 'where', [('name', '=', 'target1')]),
                    ])
            self.assertEqual(one2manys, [one2many1])
            one2manys = one2many.search([
                    ('targets', 'not where', [('name', '=', 'target1')]),
                    ])
            self.assertEqual(one2manys, [])

            one2many2, = one2many.create([{
                        'name': 'origin2',
                        }])
            self.assert_(one2many2)

            self.assertEqual(one2many2.targets, ())

            one2manys = one2many.search([
                    ('targets', '=', None),
                    ])
            self.assertEqual(one2manys, [one2many2])

            one2many.write([one2many1], {
                    'targets': [
                        ('write', [target1.id], {
                                'name': 'target1bis',
                                }),
                        ],
                    })
            self.assertEqual(target1.name, 'target1bis')

            target2, = one2many_target.create([{
                        'name': 'target2',
                        }])
            one2many.write([one2many1], {
                    'targets': [
                        ('add', [target2.id]),
                        ],
                    })
            self.assertEqual(one2many1.targets,
                (target1, target2))

            one2many.write([one2many1], {
                    'targets': [
                        ('remove', [target2.id]),
                        ],
                    })
            self.assertEqual(one2many1.targets, (target1,))
            target2, = one2many_target.search([
                    ('id', '=', target2.id),
                    ])
            self.assert_(target2)

            one2many.write([one2many1], {
                    'targets': [
                        ('remove', [target1.id]),
                        ],
                    })
            self.assertEqual(one2many1.targets, ())
            targets = one2many_target.search([
                    ('id', 'in', [target1.id, target2.id]),
                    ])
            self.assertEqual(targets, [target1, target2])

            one2many.write([one2many1], {
                    'targets': [
                        ('add', [target1.id, target2.id]),
                        ],
                    })
            self.assertEqual(one2many1.targets,
                (target1, target2))

            one2many.write([one2many1], {
                    'targets': [
                        ('copy', [target1.id], {'name': 'copy1'}),
                        ],
                    })
            targets = one2many_target.search([
                    ('id', 'not in', [target1.id, target2.id]),
                    ])
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0].name, 'copy1')

            one2many.write([one2many1], {
                    'targets': [
                        ('copy', [target2.id]),
                        ],
                    })
            self.assertEqual(len(one2many1.targets), 4)
            targets = one2many_target.search([
                    ('id', 'not in', [target1.id, target2.id]),
                    ])
            self.assertEqual(len(targets), 2)
            names = set([target.name for target in targets])
            self.assertEqual(names, set(('copy1', 'target2')))

            copy_ids = [target.id for target in targets]
            one2many.write([one2many1], {
                    'targets': [
                        ('delete', [target2.id] + copy_ids),
                        ],
                    })
            self.assertEqual(one2many1.targets, (target1,))
            targets = one2many_target.search([
                    ('id', '=', target2.id),
                    ])
            self.assertEqual(targets, [])

            transaction.rollback()

        self.assertRaises(UserError, One2manyRequired.create, [{
                    'name': 'origin3',
                    }])
        transaction.rollback()

        origin3_id, = One2manyRequired.create([{
                    'name': 'origin3',
                    'targets': [
                        ('create', [{
                                    'name': 'target3',
                                    }]),
                        ],
                    }])
        self.assert_(origin3_id)

        One2manySize.create([{
                    'targets': [('create', [{}])] * 3,
                    }])
        self.assertRaises(UserError, One2manySize.create, [{
                    'targets': [('create', [{}])] * 4,
                    }])
        One2manySizePyson.create([{
                    'limit': 4,
                    'targets': [('create', [{}])] * 4,
                    }])
        self.assertRaises(UserError, One2manySizePyson.create, [{
                    'limit': 2,
                    'targets': [('create', [{}])] * 4,
                    }])

    @with_transaction()
    def test_one2many_filter(self):
        'Test one2many with filter'
        pool = Pool()
        One2ManyFilter = pool.get('test.one2many_filter')

        filtered, = One2ManyFilter.create([{
                    'targets': [('create', [
                                {'value': x} for x in range(4)])],
                    }])
        self.assertEqual(len(filtered.targets), 4)
        filtered_target, = filtered.filtered_targets
        self.assertEqual(filtered_target.value, 3)

    @with_transaction()
    def test_one2many_filter_domain(self):
        'Test one2many with filter and domain'
        pool = Pool()
        One2ManyFilterDomain = pool.get('test.one2many_filter_domain')

        filtered, = One2ManyFilterDomain.create([{
                    'targets': [('create', [
                                {'value': x} for x in range(4)])],
                    }])
        self.assertEqual(len(filtered.targets), 4)
        filtered_target, = filtered.filtered_targets
        self.assertEqual(filtered_target.value, 3)

    @with_transaction()
    def test_one2many_filter_search(self):
        "Test search on one2many with filter"
        pool = Pool()
        One2ManyFilter = pool.get('test.one2many_filter')

        One2ManyFilter.create([{
                    'targets': [('create', [{'value': -1}])],
                    }])

        result = One2ManyFilter.search([('targets', '!=', None)])
        self.assertEqual(len(result), 1)

        result = One2ManyFilter.search([('filtered_targets', '!=', None)])
        self.assertEqual(len(result), 0)

        result = One2ManyFilter.search([('targets.value', '=', -1)])
        self.assertEqual(len(result), 1)

        result = One2ManyFilter.search([('filtered_targets.value', '=', -1)])
        self.assertEqual(len(result), 0)

    @with_transaction()
    def test_many2many(self):
        'Test Many2Many'
        pool = Pool()
        Many2many = pool.get('test.many2many')
        Many2manyTarget = pool.get('test.many2many.target')
        Many2manyRequired = pool.get('test.many2many_required')
        Many2manyReference = pool.get('test.many2many_reference')
        Many2manyReferenceTarget = pool.get('test.many2many_reference.target')
        Many2manySizeTarget = pool.get('test.many2many_size.target')
        transaction = Transaction()

        for many2many, many2many_target in (
                (Many2many, Many2manyTarget),
                (Many2manyReference, Many2manyReferenceTarget),
                ):
            many2many1, = many2many.create([{
                        'name': 'origin1',
                        'targets': [
                            ('create', [{
                                        'name': 'target1',
                                        }]),
                            ],
                        }])
            self.assert_(many2many1)

            self.assertEqual(len(many2many1.targets), 1)
            target1, = many2many1.targets

            many2manys = many2many.search([
                    ('targets', '=', 'target1'),
                    ])
            self.assertEqual(many2manys, [many2many1])

            many2manys = many2many.search([
                    ('targets', '!=', 'target1'),
                    ])
            self.assertEqual(many2manys, [])

            many2manys = many2many.search([
                    ('targets', 'in', [target1.id]),
                    ])
            self.assertEqual(many2manys, [many2many1])

            many2manys = many2many.search([
                    ('targets', 'in', [0]),
                    ])
            self.assertEqual(many2manys, [])

            many2manys = many2many.search([
                    ('targets', 'not in', [target1.id]),
                    ])
            self.assertEqual(many2manys, [])

            many2manys = many2many.search([
                    ('targets', 'not in', [0]),
                    ])
            self.assertEqual(many2manys, [many2many1])

            many2manys = many2many.search([
                    ('targets.name', '=', 'target1'),
                    ])
            self.assertEqual(many2manys, [many2many1])

            many2manys = many2many.search([
                    ('targets.name', '!=', 'target1'),
                    ])
            self.assertEqual(many2manys, [])

            many2manys = many2many.search([
                    ('targets', 'where', [('name', '=', 'target1')]),
                    ])
            self.assertEqual(many2manys, [many2many1])
            many2manys = many2many.search([
                    ('targets', 'not where', [('name', '=', 'target1')]),
                    ])
            self.assertEqual(many2manys, [])

            many2many2, = many2many.create([{
                        'name': 'origin2',
                        }])
            self.assert_(many2many2)

            self.assertEqual(many2many2.targets, ())

            many2manys = many2many.search([
                    ('targets', '=', None),
                    ])
            self.assertEqual(many2manys, [many2many2])

            many2many.write([many2many1], {
                    'targets': [
                        ('write', [target1.id], {
                                'name': 'target1bis',
                                }),
                        ],
                    })
            self.assertEqual(target1.name, 'target1bis')

            target2, = many2many_target.create([{
                        'name': 'target2',
                        }])
            many2many.write([many2many1], {
                    'targets': [
                        ('add', [target2.id]),
                        ],
                    })
            self.assertEqual(many2many1.targets,
                (target1, target2))

            many2many.write([many2many1], {
                    'targets': [
                        ('remove', [target2.id]),
                        ],
                    })
            self.assertEqual(many2many1.targets, (target1,))
            target2, = many2many_target.search([
                    ('id', '=', target2.id),
                    ])
            self.assert_(target2)

            many2many.write([many2many1], {
                    'targets': [
                        ('remove', [target1.id]),
                        ],
                    })
            self.assertEqual(many2many1.targets, ())
            targets = many2many_target.search([
                    ('id', 'in', [target1.id, target2.id]),
                    ])
            self.assertEqual(targets, [target1, target2])

            many2many.write([many2many1], {
                    'targets': [
                        ('add', [target1.id, target2.id]),
                        ],
                    })
            self.assertEqual(many2many1.targets,
                (target1, target2))

            many2many.write([many2many1], {
                    'targets': [
                        ('copy', [target1.id], {'name': 'copy1'}),
                        ],
                    })
            targets = many2many_target.search([
                    ('id', 'not in', [target1.id, target2.id]),
                    ])
            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0].name, 'copy1')

            many2many.write([many2many1], {
                    'targets': [
                        ('copy', [target2.id]),
                        ],
                    })
            self.assertEqual(len(many2many1.targets), 4)
            targets = many2many_target.search([
                    ('id', 'not in', [target1.id, target2.id]),
                    ])
            self.assertEqual(len(targets), 2)
            names = set([target.name for target in targets])
            self.assertEqual(names, set(('copy1', 'target2')))

            copy_ids = [target.id for target in targets]
            many2many.write([many2many1], {
                    'targets': [
                        ('delete', [target2.id] + copy_ids),
                        ],
                    })
            self.assertEqual(many2many1.targets, (target1,))
            targets = many2many_target.search([
                    ('id', '=', target2.id),
                    ])
            self.assertEqual(targets, [])

            transaction.rollback()

        self.assertRaises(UserError, Many2manyRequired.create, [{
                    'name': 'origin3',
                    }])
        transaction.rollback()

        origin3_id, = Many2manyRequired.create([{
                    'name': 'origin3',
                    'targets': [
                        ('create', [{
                                    'name': 'target3',
                                    }]),
                        ],
                    }])
        self.assert_(origin3_id)

        Many2manySizeTarget.create([{
                    'name': str(i),
                    } for i in range(6)])

        transaction.rollback()

    @with_transaction()
    def test_many2many_search_where_nested_value(self):
        "Test Many2Many search where nested value"
        pool = Pool()
        Many2Many = pool.get('test.many2many')

        record, = Many2Many.create([{
                    'name': 'origin',
                    'targets': [
                        ('create', [{
                                    'name': 'target',
                                    }]),
                        ],
                    }])

        result = Many2Many.search([
                ('targets', 'where', ['OR',
                        ('name', '=', 'target'),
                        ('name', '=', 'other'),
                        ]),
                ])
        self.assertEqual(result, [record])

    @with_transaction()
    def test_many2many_filter(self):
        'Test many2many with filter'
        pool = Pool()
        Many2ManyFilter = pool.get('test.many2many_filter')

        filtered, = Many2ManyFilter.create([{
                    'targets': [('create', [
                                {'value': x} for x in range(4)])],
                    }])
        self.assertEqual(len(filtered.targets), 4)
        filtered_target, = filtered.filtered_targets
        self.assertEqual(filtered_target.value, 3)
        or_filtered_target, = filtered.or_filtered_targets
        self.assertEqual(or_filtered_target.value, 3)

    @with_transaction()
    def test_many2many_filter_domain(self):
        'Test many2many with filter and domain'
        pool = Pool()
        Many2ManyFilterDomain = pool.get('test.many2many_filter_domain')

        filtered, = Many2ManyFilterDomain.create([{
                    'targets': [('create', [
                                {'value': x} for x in range(4)])],
                    }])
        self.assertEqual(len(filtered.targets), 4)
        filtered_target, = filtered.filtered_targets
        self.assertEqual(filtered_target.value, 3)

    @with_transaction()
    def test_many2many_filter_search(self):
        "Test search on many2many with filter"
        pool = Pool()
        Many2ManyFilter = pool.get('test.many2many_filter')

        Many2ManyFilter.create([{
                    'targets': [('create', [{'value': -1}])],
                    }])

        result = Many2ManyFilter.search([('targets', '!=', None)])
        self.assertEqual(len(result), 1)

        result = Many2ManyFilter.search([('filtered_targets', '!=', None)])
        self.assertEqual(len(result), 0)

        result = Many2ManyFilter.search(
            [('or_filtered_targets', '!=', None)])
        self.assertEqual(len(result), 1)

        result = Many2ManyFilter.search([('targets.value', '=', -1)])
        self.assertEqual(len(result), 1)

        result = Many2ManyFilter.search([('filtered_targets.value', '=', -1)])
        self.assertEqual(len(result), 0)

        result = Many2ManyFilter.search(
            [('or_filtered_targets.value', '=', -1)])
        self.assertEqual(len(result), 1)

    @with_transaction()
    def test_many2many_add_to_list(self):
        "Test Many2Many add to list of records"
        pool = Pool()
        Many2Many = pool.get('test.many2many')
        Many2manyTarget = pool.get('test.many2many.target')

        record1, record2 = Many2Many.create([{'name': '1'}, {'name': '2'}])
        target, = Many2manyTarget.create([{'name': 'target'}])

        # First add to record1
        Many2Many.write([record1], {
                'targets': [
                    ('add', [target.id]),
                    ],
                })
        self.assertEqual(record1.targets, (target,))

        # Add to both records
        Many2Many.write([record1, record2], {
                'targets': [
                    ('add', [target.id]),
                    ],
                })
        self.assertEqual(record1.targets, (target,))
        self.assertEqual(record2.targets, (target,))

    @with_transaction()
    def test_many2many_tree(self):
        pool = Pool()
        Many2Many = pool.get('test.many2many_tree')

        second1, second2, second3, second4 = Many2Many.create([
                {},
                {},
                {},
                {},
                ])
        first1, first2, first3, first4 = Many2Many.create([
                {'children': [('add', [second1.id, second2.id])]},
                {'children': [('add', [second1.id, second2.id])]},
                {'children': [('add', [second3.id, second4.id])]},
                {'children': [('add', [second4.id])]},
                ])
        root1, root2 = Many2Many.create([
                {'children': [
                        ('add', [first1.id, first2.id, second1.id])]},
                {'children': [('add', [first3.id, first4.id])]},
                ])

        all_ = Many2Many.search([])

        def not_(l):
            return [r for r in all_ if r not in l]

        for clause, test in [
                ([root1.id], [second1, second2, first1, first2, root1]),
                ([second1.id], [second1]),
                ([root2.id], [second3, second4, first3, first4, root2]),
                ([], []),
                ]:
            result = Many2Many.search(
                [('parents', 'child_of', clause)])
            self.assertEqual(result, test)

            result = Many2Many.search(
                [('parents', 'not child_of', clause)])
            self.assertEqual(result, not_(test))

        for clause, test in [
                ([root1.id], [root1]),
                ([first3.id], [first3, root2]),
                ([second4.id], [second4, first3, first4, root2]),
                ([second4.id, first4.id], [second4, first3, first4,
                        root2]),
                ([], []),
                ]:
            result = Many2Many.search(
                [('parents', 'parent_of', clause)])
            self.assertEqual(result, test)

            result = Many2Many.search(
                [('parents', 'not parent_of', clause)])
            self.assertEqual(result, not_(test))

    @with_transaction()
    def test_reference(self):
        'Test Reference'
        pool = Pool()
        Reference = pool.get('test.reference')
        ReferenceTarget = pool.get('test.reference.target')
        ReferenceRequired = pool.get('test.reference_required')
        transaction = Transaction()

        target1, = ReferenceTarget.create([{
                    'name': 'target1',
                    }])
        reference1, = Reference.create([{
                    'name': 'reference1',
                    'reference': str(target1),
                    }])
        self.assert_(reference1)

        self.assertEqual(reference1.reference, target1)

        references = Reference.search([
                ('reference', '=', str(target1)),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference', '=', (target1.__name__, target1.id)),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference', '=', [target1.__name__, target1.id]),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference.name', '=', 'target1',
                    'test.reference.target'),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference', '!=', str(target1)),
                ])
        self.assertEqual(references, [])

        references = Reference.search([
                ('reference', '!=', str(target1)),
                ])
        self.assertEqual(references, [])

        references = Reference.search([
                ('reference', 'in', [str(target1)]),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference', 'in',
                    [('test.reference.target', target1.id)]),
                ])
        self.assertEqual(references, [reference1])

        references = Reference.search([
                ('reference', 'in', [None]),
                ])
        self.assertEqual(references, [])

        references = Reference.search([
                ('reference', 'not in', [str(target1)]),
                ])
        self.assertEqual(references, [])

        references = Reference.search([
                ('reference', 'not in',
                    [('test.reference.target', target1.id)]),
                ])
        self.assertEqual(references, [])

        references = Reference.search([
                ('reference', 'not in', [None]),
                ])
        self.assertEqual(references, [reference1])

        reference2, = Reference.create([{
                    'name': 'reference2',
                    }])
        self.assert_(reference2)

        self.assertEqual(reference2.reference, None)

        references = Reference.search([
                ('reference', '=', None),
                ])
        self.assertEqual(references, [reference2])

        target2, = ReferenceTarget.create([{
                    'name': 'target2',
                    }])

        Reference.write([reference2], {
                'reference': str(target2),
                })
        self.assertEqual(reference2.reference, target2)

        Reference.write([reference2], {
                'reference': None,
                })
        self.assertEqual(reference2.reference, None)

        Reference.write([reference2], {
                'reference': 'test.reference.target,',
                })
        self.assertEqual(reference2.reference, 'test.reference.target,')
        self.assertFalse(isinstance(reference2.reference, ReferenceTarget))

        Reference.write([reference2], {
                'reference': 'test.reference.target,-1',
                })
        self.assertEqual(reference2.reference, 'test.reference.target,-1')
        self.assertFalse(isinstance(reference2.reference, ReferenceTarget))

        Reference.write([reference2], {
                'reference': ('test.reference.target', target2.id),
                })
        self.assertEqual(reference2.reference, target2)

        reference3, = Reference.create([{
                    'name': 'reference3',
                    'reference': ('test.reference.target', target1.id),
                    }])
        self.assert_(reference3)

        self.assertRaises(UserError, ReferenceRequired.create, [{
                    'name': 'reference4',
                    }])
        transaction.rollback()

        self.assertRaises(UserError, ReferenceRequired.create, [{
                    'name': 'reference4',
                    'reference': str(ReferenceTarget()),
                    }])
        transaction.rollback()

        target4, = ReferenceTarget.create([{
                    'name': 'target4_id',
                    }])

        reference4, = ReferenceRequired.create([{
                    'name': 'reference4',
                    'reference': str(target4),
                    }])
        self.assert_(reference4)

    @with_transaction()
    def test_selection(self):
        'Test Selection'
        pool = Pool()
        Selection = pool.get('test.selection')
        SelectionRequired = pool.get('test.selection_required')
        transaction = Transaction()

        selection1, = Selection.create([{'select': 'arabic'}])
        self.assert_(selection1)
        self.assertEqual(selection1.select, 'arabic')
        self.assertEqual(selection1.select_string, 'Arabic')

        selection2, = Selection.create([{'select': None}])
        self.assert_(selection2)
        self.assertEqual(selection2.select, None)
        self.assertEqual(selection2.select_string, '')

        self.assertRaises(UserError, Selection.create,
            [{'select': 'chinese'}])

        selection3, = Selection.create(
            [{'select': 'arabic', 'dyn_select': '1'}])
        self.assert_(selection3)
        self.assertEqual(selection3.select, 'arabic')
        self.assertEqual(selection3.dyn_select, '1')
        self.assertEqual(selection3.dyn_select_string, '1')

        selection4, = Selection.create(
            [{'select': 'hexa', 'dyn_select': '0x3'}])
        self.assert_(selection4)
        self.assertEqual(selection4.select, 'hexa')
        self.assertEqual(selection4.dyn_select, '0x3')

        selection5, = Selection.create(
            [{'select': 'hexa', 'dyn_select': None}])
        self.assert_(selection5)
        self.assertEqual(selection5.select, 'hexa')
        self.assertEqual(selection5.dyn_select, None)

        self.assertRaises(UserError, Selection.create,
            [{'select': 'arabic', 'dyn_select': '0x3'}])
        self.assertRaises(UserError, Selection.create,
            [{'select': 'hexa', 'dyn_select': '3'}])

        selection7, = Selection.create(
            [{'dyn_select_static': '1'}])
        self.assertEqual(selection7.dyn_select_static, '1')
        self.assertEqual(selection7.dyn_select_static_string, '1')

        self.assertRaises(UserError, SelectionRequired.create, [{}])
        transaction.rollback()

        self.assertRaises(UserError, SelectionRequired.create,
            [{'select': None}])
        transaction.rollback()

        selection6, = SelectionRequired.create([{'select': 'latin'}])
        self.assert_(selection6)
        self.assertEqual(selection6.select, 'latin')

    @with_transaction()
    def test_dict(self):
        'Test Dict'
        pool = Pool()
        Dict = pool.get('test.dict')
        DictSchema = pool.get('test.dict.schema')
        DictDefault = pool.get('test.dict_default')
        DictRequired = pool.get('test.dict_required')
        transaction = Transaction()

        DictSchema.create([{
                    'name': 'a',
                    'string': 'A',
                    'type_': 'integer',
                    }, {
                    'name': 'b',
                    'string': 'B',
                    'type_': 'integer',
                    }, {
                    'name': 'type',
                    'string': 'Type',
                    'type_': 'selection',
                    'selection': ('arabic: Arabic\n'
                        'hexa: Hexadecimal'),
                    }])

        dict1, = Dict.create([{
                    'dico': {'a': 1, 'b': 2},
                    }])
        self.assert_(dict1.dico == {'a': 1, 'b': 2})

        Dict.write([dict1], {'dico': {'z': 26}})
        self.assert_(dict1.dico == {'z': 26})

        dict1.dico = {
            'a': 1,
            'type': 'arabic',
            }
        dict1.save()
        self.assertEqual(dict1.dico, {'a': 1, 'type': 'arabic'})
        self.assertEqual(dict1.dico_string, {
                'a': 1,
                'type': 'Arabic',
                })
        self.assertEqual(dict1.dico_string_keys, {
                'a': 'A',
                'type': 'Type',
                })

        dict2, = Dict.create([{}])
        self.assert_(dict2.dico is None)

        dict3, = DictDefault.create([{}])
        self.assert_(dict3.dico == {'a': 1})

        self.assertRaises(UserError, DictRequired.create, [{}])
        transaction.rollback()

        dict4, = DictRequired.create([{'dico': dict(a=1)}])
        self.assert_(dict4.dico == {'a': 1})

        self.assertRaises(UserError, DictRequired.create,
            [{'dico': {}}])

    @with_transaction()
    @unittest.skipIf(
        backend.name() != 'postgresql', 'jsonb only suported by postgresql')
    def test_dict_jsonb(self):
        'Test Dict stored as jsonb'
        pool = Pool()
        Dict = pool.get('test.dict_jsonb')
        connection = Transaction().connection
        cursor = connection.cursor()

        Database = backend.get('Database')
        if Database().get_version(connection) < (9, 2):
            return

        cursor.execute('ALTER TABLE "%s" '
            'ALTER COLUMN dico TYPE json USING dico::json' % Dict._table)

        dict1, = Dict.create([{
                    'dico': {'a': 1, 'b': 2},
                    }])
        self.assert_(dict1.dico == {'a': 1, 'b': 2})

        Dict.write([dict1], {'dico': {'z': 26}})
        self.assert_(dict1.dico == {'z': 26})

    @with_transaction()
    def test_binary(self):
        'Test Binary'
        pool = Pool()
        Binary = pool.get('test.binary')
        BinaryDefault = pool.get('test.binary_default')
        BinaryRequired = pool.get('test.binary_required')
        transaction = Transaction()

        bin1, = Binary.create([{
                    'binary': fields.Binary.cast(b'foo'),
                    }])
        self.assert_(bin1.binary == fields.Binary.cast(b'foo'))

        Binary.write([bin1], {'binary': fields.Binary.cast(b'bar')})
        self.assert_(bin1.binary == fields.Binary.cast(b'bar'))

        with transaction.set_context({'test.binary.binary': 'size'}):
            bin1_size = Binary(bin1.id)
            self.assert_(bin1_size.binary == len(b'bar'))
            self.assert_(bin1_size.binary != fields.Binary.cast(b'bar'))

        bin2, = Binary.create([{}])
        self.assert_(bin2.binary is None)

        bin3, = BinaryDefault.create([{}])
        self.assert_(bin3.binary == fields.Binary.cast(b'default'))

        self.assertRaises(UserError, BinaryRequired.create, [{}])
        transaction.rollback()

        bin4, = BinaryRequired.create([{
                    'binary': fields.Binary.cast(b'baz'),
                    }])
        self.assert_(bin4.binary == fields.Binary.cast(b'baz'))

        self.assertRaises(UserError, BinaryRequired.create,
            [{'binary': fields.Binary.cast(b'')}])

    @with_transaction()
    def test_binary_filestorage(self):
        "Test Binary FileStorage"
        pool = Pool()
        Binary = pool.get('test.binary_filestorage')
        transaction = Transaction()

        bin1, = Binary.create([{
                    'binary': fields.Binary.cast(b'foo'),
                    }])
        self.assertEqual(bin1.binary, fields.Binary.cast(b'foo'))
        self.assertTrue(bin1.binary_id)

        Binary.write([bin1], {'binary': fields.Binary.cast(b'bar')})
        self.assertEqual(bin1.binary, fields.Binary.cast(b'bar'))

        with transaction.set_context(
                {'test.binary_filestorage.binary': 'size'}):
            bin1_size = Binary(bin1.id)
            self.assertEqual(bin1_size.binary, len(b'bar'))

        Binary.write([bin1], {'binary': None})
        self.assertEqual(bin1.binary, None)
        self.assertEqual(bin1.binary_id, None)

    @with_transaction()
    def test_many2one(self):
        'Test Many2One'
        pool = Pool()
        Many2oneDomainValidation = pool.get('test.many2one_domainvalidation')
        Many2oneOrderby = pool.get('test.many2one_orderby')
        Many2oneTarget = pool.get('test.many2one_target')
        Many2oneSearch = pool.get('test.many2one_search')
        transaction = Transaction()

        # Not respecting the domain raise an Error
        m2o_1, = Many2oneTarget.create([{'value': 1}])
        self.assertRaises(UserError, Many2oneDomainValidation.create,
            [{'many2one': m2o_1}])

        # Respecting the domain works
        m2o_6, = Many2oneTarget.create([{'value': 6}])
        domain, = Many2oneDomainValidation.create([{'many2one': m2o_6}])
        self.assert_(domain)
        self.assertEqual(domain.many2one.value, 6)

        # Inactive records are taken into account
        m2o_6.active = False
        m2o_6.save()
        domain.dummy = 'Dummy'
        domain.save()

        # Testing order_by
        for value in (5, 3, 2):
            m2o, = Many2oneTarget.create([{'value': value}])
            Many2oneOrderby.create([{'many2one': m2o}])

        search = Many2oneOrderby.search([], order=[('many2one', 'ASC')])
        self.assertTrue(all(x.many2one.value <= y.many2one.value
                for x, y in zip(search, search[1:])))

        search = Many2oneOrderby.search([],
            order=[('many2one.id', 'ASC')])
        self.assertTrue(all(x.many2one.id <= y.many2one.id
                for x, y in zip(search, search[1:])))

        search = Many2oneOrderby.search([],
            order=[('many2one.value', 'ASC')])
        self.assertTrue(all(x.many2one.value <= y.many2one.value
                for x, y in zip(search, search[1:])))

        transaction.rollback()

        target1, target2 = Many2oneTarget.create([
                {'value': 1},
                {'value': 2},
                ])

        search1, search2 = Many2oneSearch.create([
                {'many2one': target1.id},
                {'many2one': target2.id},
                ])

        # Search join
        Many2oneSearch.target_search = 'join'
        self.assertEqual(Many2oneSearch.search([
                    ('many2one.value', '=', 1),
                    ]), [search1])

        # Search subquery
        Many2oneSearch.target_search = 'subquery'
        self.assertEqual(Many2oneSearch.search([
                    ('many2one.value', '=', 1),
                    ]), [search1])

        transaction.rollback()

        for model in ['test.many2one_tree', 'test.many2one_mptt']:
            pool = Pool()
            Many2One = pool.get(model)

            root1, root2 = Many2One.create([{}, {}])
            first1, first2, first3, first4 = Many2One.create([
                    {'many2one': root1.id},
                    {'many2one': root1.id},
                    {'many2one': root2.id},
                    {'many2one': root2.id},
                    ])
            second1, second2, second3, second4 = Many2One.create([
                    {'many2one': first1.id},
                    {'many2one': first1.id},
                    {'many2one': first2.id},
                    {'many2one': first2.id},
                    ])
            all_ = Many2One.search([])

            def not_(l):
                return [r for r in all_ if r not in l]

            for clause, test in [
                    ([root1.id], [root1, first1, first2,
                            second1, second2, second3, second4]),
                    ([second1.id], [second1]),
                    ([root2.id], [root2, first3, first4]),
                    ([first2.id, first3.id], [first2, first3,
                            second3, second4]),
                    ([], []),
                    ]:
                result = Many2One.search(
                    [('many2one', 'child_of', clause)])
                self.assertEqual(result, test)

                result = Many2One.search(
                    [('many2one', 'not child_of', clause)])
                self.assertEqual(result, not_(test))

            for clause, test in [
                    ([root1.id], [root1]),
                    ([first3.id], [root2, first3]),
                    ([second4.id], [root1, first2, second4]),
                    ([second4.id, first4.id], [root1, root2,
                            first2, first4, second4]),
                    ([], []),
                    ]:
                result = Many2One.search(
                    [('many2one', 'parent_of', clause)])
                self.assertEqual(result, test)

                result = Many2One.search(
                    [('many2one', 'not parent_of', clause)])
                self.assertEqual(result, not_(test))

            transaction.rollback()

    @with_transaction()
    def test_many2one_no_foreign_key(self):
        "Test Many2One without Foreign Key"
        pool = Pool()
        Many2OneNoForeignKey = pool.get('test.many2one_no_foreign_key')
        Many2OneTargetStorage = pool.get('test.many2one_target_storage')

        record = Many2OneNoForeignKey(many2one=1)
        record.save()

        self.assertIsInstance(record.many2one, Many2OneTargetStorage)

    @with_transaction()
    def test_timedelta(self):
        'Test timedelta'
        pool = Pool()
        Timedelta = pool.get('test.timedelta')
        TimedeltaDefault = pool.get('test.timedelta_default')
        TimedeltaRequired = pool.get('test.timedelta_required')
        transaction = Transaction()

        minute = datetime.timedelta(minutes=1)
        hour = datetime.timedelta(hours=1)
        day = datetime.timedelta(days=1)
        default_timedelta = datetime.timedelta(seconds=3600)

        timedelta1, = Timedelta.create([{
                    'timedelta': hour,
                    }])
        self.assert_(timedelta1)
        self.assertEqual(timedelta1.timedelta, hour)

        timedelta = Timedelta.search([
                ('timedelta', '=', hour),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '=', day),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '=', None),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '!=', day),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '!=', None),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', 'in', [hour]),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', 'in', [day]),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', 'in', [minute]),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', 'in', [None]),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', 'in', []),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', 'not in', [hour]),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', 'not in', [day]),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', 'not in', [None]),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', 'not in', []),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '<', day),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '<', minute),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '<', hour),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '<=', hour),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '<=', minute),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '<=', day),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '>', day),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '>', minute),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '>', hour),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '>=', day),
                ])
        self.assertEqual(timedelta, [])

        timedelta = Timedelta.search([
                ('timedelta', '>=', minute),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta = Timedelta.search([
                ('timedelta', '>=', hour),
                ])
        self.assertEqual(timedelta, [timedelta1])

        timedelta2, = Timedelta.create([{
                    'timedelta': minute,
                    }])
        self.assert_(timedelta2)
        self.assertEqual(timedelta2.timedelta, minute)

        timedelta = Timedelta.search([
                ('timedelta', '=', minute),
                ])
        self.assertEqual(timedelta, [timedelta2])

        timedelta = Timedelta.search([
                ('timedelta', 'in', [minute, hour]),
                ])
        self.assertEqual(timedelta, [timedelta1, timedelta2])

        timedelta = Timedelta.search([
                ('timedelta', 'not in', [minute, hour]),
                ])
        self.assertEqual(timedelta, [])

        timedelta3, = Timedelta.create([{}])
        self.assert_(timedelta3)
        self.assertEqual(timedelta3.timedelta, None)

        timedelta4, = TimedeltaDefault.create([{}])
        self.assert_(timedelta4)
        self.assertEqual(timedelta4.timedelta, default_timedelta)

        Timedelta.write([timedelta1], {
                'timedelta': minute,
                })
        self.assertEqual(timedelta1.timedelta, minute)

        Timedelta.write([timedelta2], {
                'timedelta': day,
                })
        self.assertEqual(timedelta2.timedelta, day)

        self.assertRaises(Exception, Timedelta.create, [{
                    'timedelta': 'test',
                    }])

        self.assertRaises(Exception, Timedelta.write, [timedelta1], {
                'timedelta': 'test',
                })

        self.assertRaises(Exception, Timedelta.create, [{
                    'timedelta': 1,
                    }])

        self.assertRaises(Exception, Timedelta.write, [timedelta1], {
                'timedelta': 1,
                })

        self.assertRaises(UserError, TimedeltaRequired.create, [{}])
        transaction.rollback()

        timedelta6, = TimedeltaRequired.create([{
                    'timedelta': day,
                    }])
        self.assert_(timedelta6)

        timedelta7, = Timedelta.create([{
                    'timedelta': None,
                    }])
        self.assert_(timedelta7)


def suite():
    return unittest.TestLoader().loadTestsFromTestCase(FieldsTestCase)
