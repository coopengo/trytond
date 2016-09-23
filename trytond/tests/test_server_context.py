# This file is part of Coog. The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest

from trytond.server_context import ServerContext


class ServerContextTestCase(unittest.TestCase):
    'Test Server Context'

    def test_server_context(self):
        with ServerContext().set_context(a=1):
            self.assertEqual(ServerContext().context.get('a'), 1)
            self.assertEqual(ServerContext().context.get('b', 10), 10)
            self.assertEqual(ServerContext().get('a'), 1)
            self.assertEqual(ServerContext().get('b', 10), 10)

            with ServerContext().set_context(a=10):
                self.assertEqual(ServerContext().context.get('a'), 10)
            self.assertEqual(ServerContext().context.get('a'), 1)

            with ServerContext().set_context(c=10):
                self.assertEqual(ServerContext().context.get('a'), 1)
                self.assertEqual(ServerContext().context.get('c'), 10)
            self.assertEqual(ServerContext().context.get('c', 1), 1)

            self.assertEqual(ServerContext().context, {'a': 1})
        self.assertEqual(ServerContext().context, {})


def suite():
    func = unittest.TestLoader().loadTestsFromTestCase
    suite = unittest.TestSuite()
    for testcase in (ServerContextTestCase,):
        suite.addTests(func(testcase))
    return suite
