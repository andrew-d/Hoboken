# -*- coding: utf-8 -*-
import os
import yaml

from hoboken.tests.compat import parametrize, parametrize_class, unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.cookies import *
from hoboken.six import iteritems, PY3, text_type


def _e(val):
    if isinstance(val, text_type):
        return val.encode('latin-1')

    return val


class TestQuoting(unittest.TestCase):
    def test_escape_table(self):
        from hoboken.objects.mixins.cookies import _escape_table

        for k, v in iteritems(_escape_table):
            if PY3:
                self.assertTrue(isinstance(k, int))
                self.assertTrue(isinstance(v, bytes))
            else:
                self.assertTrue(isinstance(k, bytes))
                self.assertTrue(isinstance(v, bytes))

    def test_unquoter_table(self):
        from hoboken.objects.mixins.cookies import _unquoter_table

        for k, v in iteritems(_unquoter_table):
            self.assertTrue(isinstance(k, bytes))
            self.assertTrue(isinstance(v, bytes))

    def test_needs_quoting(self):
        from hoboken.objects.mixins.cookies import _needs_quoting

        # Might want to test everything, but that seems rather pointless.
        self.assertTrue(_needs_quoting(b"\xff"))
        self.assertFalse(_needs_quoting(b"asdf"))

    def test_quote(self):
        from hoboken.objects.mixins.cookies import _quote

        self.assertEqual(_quote(b'asdf'), b'asdf')
        self.assertEqual(_quote(b'\xffa\x99'), b'"\\377a\\231"')

    def test_unquote(self):
        from hoboken.objects.mixins.cookies import _unquote

        self.assertEqual(_unquote(b'asdf'), b'asdf')
        self.assertEqual(_unquote(b'"asdf"'), b'asdf')
        self.assertEqual(_unquote(b'"\000\001"'), b'\x00\x01')


# Load tests.
tests_file = os.path.join(os.path.dirname(__file__), 'cookie_tests.yaml')

with open(tests_file, 'rb') as f:
    test_data = f.read()

cookie_tests = yaml.load_all(test_data)


@parametrize_class
class TestParsing(unittest.TestCase):
    @parametrize('param', cookie_tests)
    def test_cookie_parsing(self, param):
        if param is None:
            return

        input = _e(param['input'])

        morsels = parse_cookie(input)

        for test_morsel in param['morsels']:
            morsel_name = _e(test_morsel['name'])
            morsel_value = _e(test_morsel['value'])

            # Note: this will raise an exception if it doesn't exist, which
            # is what we want.
            morsel = morsels.pop(morsel_name)
            self.assertEqual(morsel.value, morsel_value)

            for attr in test_morsel.get('attributes', []):
                test_name, test_val = attr.popitem()
                actual_val = getattr(morsel, test_name)
                self.assertEqual(actual_val, _e(test_val))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQuoting))
    suite.addTest(unittest.makeSuite(TestParsing))

    return suite
