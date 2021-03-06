# -*- coding: utf-8 -*-
import os
import yaml

from hoboken.tests.compat import parametrize, parametrize_class, unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.headers import ResponseHeaders
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
            setattr(m, name, _e(val))

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
        txt = b'foobar'.decode('ascii')
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

    def test_morsel_equality(self):
        m1 = Morsel(b'foo', b'bar')
        m2 = Morsel(b'foo', b'other')
        self.assertNotEqual(m1, m2)

        m2.value = b'bar'
        self.assertEqual(m1, m2)

        m1.httponly = True
        self.assertNotEqual(m1, m2)

        m2.httponly = True
        self.assertEqual(m1, m2)

    def test_morsel_compare_other(self):
        m = Morsel(b'foo')
        self.assertFalse(m == b'foo')
        self.assertFalse(b'foo' == m)


class TestWSGIRequestCookiesMixin(unittest.TestCase):
    def setUp(self):
        class MixedIn(WSGIRequestCookiesMixin):
            headers = {}

        self.c = MixedIn()

    def test_defaults_to_empty(self):
        self.assertEqual(self.c.cookies, {})

    def test_will_parse_cookies(self):
        self.c.headers['Cookie'] = b'foo=bar'
        self.assertIn(b'foo', self.c.cookies)

        c = self.c.cookies[b'foo']
        self.assertEqual(c.value, b'bar')

        # Call again to assert that caching works.
        self.c.cookies


class TestWSGIResponseCookiesMixin(unittest.TestCase):
    def setUp(self):
        class MixedIn(WSGIResponseCookiesMixin):
            def __init__(self):
                self.headers = ResponseHeaders()
                super(MixedIn, self).__init__()

        self.c = MixedIn()

    def assert_cookies(self, *cookies):
        # Make our cookies MultiDict into a sorted list of (name, val) tuples.
        have_c = sorted(map(
            lambda tup: (tup[0], tup[1].value),
            self.c.cookies.iteritems(multi=True)
        ))
        check_c = sorted(cookies)
        self.assertEqual(have_c, check_c)

    def test_defaults_to_empty(self):
        self.assert_cookies()

    def test_will_serialize(self):
        self.c.cookies['foo'] = Morsel(b'foo', b'bar')
        self.assert_cookies((b'foo', b'bar'))

    def test_will_serialize_multiple(self):
        self.c.cookies['foo'] = Morsel(b'foo', b'bar')
        self.c.cookies.add('foo', Morsel(b'foo', b'asdf'))
        self.assert_cookies((b'foo', b'bar'), (b'foo', b'asdf'))

        self.assertEqual(sorted(self.c.headers),
                         [('Set-Cookie', 'foo=asdf'), ('Set-Cookie', 'foo=bar')]
                         )

    def test_will_override_name(self):
        self.c.cookies['name'] = Morsel(b'bad', b'val')
        self.assertEqual(sorted(self.c.headers),
                         [('Set-Cookie', 'name=val')]
                         )

    def test_cookies_setter(self):
        self.c.cookies['foo'] = Morsel(b'foo', b'bar')
        self.c.cookies = {'aaa': Morsel(b'aaa', b'bbb')}
        self.assert_cookies((b'aaa', b'bbb'))

    def test_cookies_deleter(self):
        self.c.cookies['foo'] = Morsel(b'foo', b'bar')
        del self.c.cookies
        self.assert_cookies()



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQuoting))
    suite.addTest(unittest.makeSuite(TestParsingAndSerializing))
    suite.addTest(unittest.makeSuite(TestMiscellaneous))
    suite.addTest(unittest.makeSuite(TestWSGIRequestCookiesMixin))

    return suite
