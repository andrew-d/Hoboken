# -*- coding: utf-8 -*-
import os
import yaml

from hoboken.tests.compat import parametrize, parametrize_class, unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins import cookies
from hoboken.objects.mixins.cookies import *
from hoboken.six import iteritems, PY3, text_type

# Done after the 'from *' above, as that clobbers datetime.
import datetime

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

    def test_unquote_handles_bool(self):
        from hoboken.objects.mixins.cookies import _unquote

        self.assertEqual(_unquote(True), True)
        self.assertEqual(_unquote(False), False)


# Load all tests.
parse_tests_file = os.path.join(os.path.dirname(__file__),
                                 'cookie_parsing_tests.yaml')
ser_tests_file = os.path.join(os.path.dirname(__file__),
                              'cookie_serialization_tests.yaml')

with open(parse_tests_file, 'rb') as f:
    test_data1 = f.read()

with open(ser_tests_file, 'rb') as f:
    test_data2 = f.read()

parse_tests = yaml.load_all(test_data1)
serialization_tests = yaml.load_all(test_data2)


@parametrize_class
class TestParsingAndSerializing(unittest.TestCase):
    @parametrize('param', parse_tests)
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

            attrs = test_morsel.get('attributes', [])
            while len(attrs):
                test_name, test_val = attrs.popitem()

                print("Testing: %r / %r" % (test_name, test_val))
                actual_val = getattr(morsel, test_name)
                self.assertEqual(actual_val, _e(test_val))

    @parametrize('param', serialization_tests)
    def test_cookie_serialization(self, param):
        if not param:
            return

        name = _e(param['values']['name'])
        value = _e(param['values']['value'])

        m = Morsel(name, value)
        for name, val in iteritems(param['values']['attributes']):
            setattr(m, name, val)

        output = _e(param['output'])
        self.assertEqual(m.serialize(), output)


class TestMiscellaneous(unittest.TestCase):
    def test_serialize_max_age(self):
        d1 = datetime.datetime(2013, 1, 11, 20, 0, 0)
        d2 = datetime.datetime(2013, 1, 11, 20, 0, 10)
        td = d2 - d1
        self.assertEqual(serialize_max_age(td), b'10')

    def test_serialize_cookie_date_with_None(self):
        self.assertEqual(serialize_cookie_date(None), None)

    def test_serialize_cookie_date_with_text(self):
        txt = 'foobar'.decode('ascii')
        self.assertEqual(serialize_cookie_date(txt), b'foobar')

    def test_serialize_cookie_date_with_Number(self):
        d = datetime.datetime(2013, 1, 11, 20, 0, 0)
        expected = b'Fri, 11-Jan-2013 20:00:10 GMT'

        with patch.object(cookies, '_utcnow') as mock:
            mock.return_value = d

            v = serialize_cookie_date(10)
            self.assertEqual(v, expected)

    def test_serialize_cookie_date_with_datetime(self):
        d = datetime.datetime(2013, 1, 11, 20, 0, 0)
        v = serialize_cookie_date(d)
        self.assertEqual(v, b'Fri, 11-Jan-2013 20:00:00 GMT')


class TestWSGIRequestCookiesMixin(unittest.TestCase):
    def setUp(self):
        class MixedIn(WSGIRequestCookiesMixin):
            headers = {}

        self.c = MixedIn()

    def test_defaults_to_empty(self):
        self.assertEqual(self.c.cookies, {})

    def test_will_parse_cookies(self):
        self.c.headers['Cookie'] = b'foo=bar'
        self.assertIn('foo', self.c.cookies)

        c = self.c.cookies['foo']
        self.assertEqual(c.value, b'bar')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQuoting))
    suite.addTest(unittest.makeSuite(TestParsingAndSerializing))
    suite.addTest(unittest.makeSuite(TestMiscellaneous))
    suite.addTest(unittest.makeSuite(TestWSGIRequestCookiesMixin))

    return suite
