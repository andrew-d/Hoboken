# -*- coding: utf-8 -*-

import copy

from hoboken.tests.compat import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.headers import EnvironHeaders, ResponseHeaders


class TestEnvironHeaders(unittest.TestCase):
    def setUp(self):
        self.environ = {
            'HTTP_HEADER': b'value',
            'HTTP_OTHER_HEADER': b'other'
        }
        self.h = EnvironHeaders(self.environ)

    def test_realname(self):
        self.assertEqual(self.h._realname('header'), 'HTTP_HEADER')
        self.assertEqual(self.h._realname('dash-header'), 'HTTP_DASH_HEADER')

        self.assertEqual(self.h._realname(b'byte-header'), 'HTTP_BYTE_HEADER')

    def test_get_item(self):
        self.assertEqual(self.h['header'], b'value')

    def test_set_item(self):
        self.h['foo'] = 'bar'
        self.assertEqual(self.h['foo'], b'bar')

        self.h['header'] = 'baz'
        self.assertEqual(self.h['header'], b'baz')

    def test_delete_item(self):
        del self.h['header']
        self.assertNotIn('HTTP_HEADER', self.environ)

    def test_contains(self):
        self.h['Foo'] = 'bar'
        self.assertIn('Foo', self.h)
        self.assertNotIn('Bad', self.h)

    def test_misc(self):
        self.assertEqual(len(self.h), 2)

        self.assertEqual(sorted(self.h.keys()), ['Header', 'Other-Header'])

    def test_with_no_environ(self):
        env = {}
        h = EnvironHeaders(env)

        h['Header'] = b'123'
        self.assertEqual(h['Header'], b'123')

    def test_to_list(self):
        l = sorted(self.h.to_list())
        self.assertEqual(l, [('Header', b'value'), ('Other-Header', b'other')])


class TestResponseHeaders(unittest.TestCase):
    def setUp(self):
        self.h = ResponseHeaders()
        self.h['Foo'] = 'bar'
        self.e = ResponseHeaders()

    def asserth(self, val):
        self.assertEqual(sorted(list(self.h.iteritems())), sorted(val))

    def asserte(self, val):
        self.assertEqual(sorted(list(self.e.iteritems())), sorted(val))

    def test_constructor(self):
        self.asserte([])

    def test_constructor_with_list(self):
        self.h = ResponseHeaders([('Foo', 'bar')])
        self.asserth([('Foo', 'bar')])

    def test_getting_and_setting(self):
        # Test with str (default, set above)
        self.assertEqual(self.h['foo'], b'bar')
        self.asserth([('Foo', 'bar')])

        # Test with bytes (really only useful on Py3)
        self.h['foo'] = b'bar'
        self.assertEqual(self.h['foo'], b'bar')
        self.asserth([('Foo', 'bar')])

    def test_normalizing(self):
        self.e['A-header-NAME'] = 'foo'

        for n in ['A-Header-Name', 'a-header-name', 'A-HEADER-NAME']:
            self.assertIn(n, self.e)

    def test_will_check_invalid_name(self):
        with self.assertRaises(ValueError):
            self.h['Invalid\r\nName'] = 'foo'

    def test_will_check_invalid_value(self):
        with self.assertRaises(ValueError):
            self.h['Header'] = 'Invalid\r\nVal'

    def test_multiple_headers(self):
        self.e.add('Foo', 'bar')
        self.e.add('Foo', 'asdf')
        self.asserte([
            ('Foo', 'bar'),
            ('Foo', 'asdf'),
        ])

        self.e['Foo'] = 'baz'
        self.asserte([('Foo', 'baz')])

    def test_deleting(self):
        del self.h['Foo']

        self.asserth([])

        with self.assertRaises(KeyError):
            del self.h['Foo']

    def test_len(self):
        self.assertEqual(len(self.h), 1)

    def test_iter(self):
        self.assertEqual(list(iter(self.h)), [
            ('Foo', 'bar')
        ])

    def test_contains(self):
        self.assertTrue('Foo' in self.h)
        self.assertFalse('Foo' in self.e)

    def test_clear(self):
        self.asserth([('Foo', 'bar')])
        self.h.clear()
        self.asserth([])

    def test_copy(self):
        self.assertEqual(self.h.copy(), self.h)

    def test_copy_module(self):
        c = copy.copy(self.h)
        self.assertTrue(isinstance(c, ResponseHeaders))
        self.assertEqual(c, self.h)
        self.assertIsNot(c, self.h)

    def test_iteration(self):
        self.assertEqual(list(self.h.iteritems()),
                         [('Foo', 'bar')]
                         )

        self.assertEqual(list(self.h.iterkeys()), ['Foo'])
        self.assertEqual(list(self.h.itervalues()), ['bar'])

    def test_get_all(self):
        self.h.add('Foo', 'baz')
        self.h.add('Foo', 'asdf')

        self.assertEqual(self.h.get_all('Foo'), [
            ('Foo', 'bar'),
            ('Foo', 'baz'),
            ('Foo', 'asdf'),
        ])

    def test_extend(self):
        self.e.extend({'Foo': 'bar', 'Header': ['one', 'two']})
        self.asserte([
            ('Foo', 'bar'),
            ('Header', 'one'),
            ('Header', 'two'),
        ])

    def test_extend_with_other_iterable(self):
        def foo():
            for i in range(3):
                yield "Header%s" % i, str(i)

        self.e.extend(foo())
        self.asserte([
            ('Header0', '0'),
            ('Header1', '1'),
            ('Header2', '2'),
        ])

    def test_remove(self):
        self.assertTrue(self.h.remove('Foo'))
        self.assertFalse(self.h.remove('Qqqq'))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnvironHeaders))
    suite.addTest(unittest.makeSuite(TestResponseHeaders))

    return suite

