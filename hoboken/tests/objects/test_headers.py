# -*- coding: utf-8 -*-

from hoboken.tests.compat import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.headers import WSGIHeaders

class TestWSGIHeaders(unittest.TestCase):
    def setUp(self):
        self.environ = {
            'HTTP_HEADER': b'value',
            'HTTP_OTHER_HEADER': b'other'
        }
        self.h = WSGIHeaders(self.environ)

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
        self.assertTrue('HTTP_HEADER' not in self.environ)

    def test_contains(self):
        self.h['Foo'] = 'bar'
        self.assertTrue('Foo' in self.h)
        self.assertFalse('Bad' in self.h)

    def test_misc(self):
        self.assertEqual(len(self.h), 2)

        self.assertEqual(sorted(self.h.keys()), ['Header', 'Other-Header'])

    def test_with_no_environ(self):
        env = {}
        h = WSGIHeaders(env)

        h['Header'] = b'123'
        self.assertEqual(h['Header'], b'123')

    def test_to_list(self):
        l = sorted(self.h.to_list())
        self.assertEqual(l, [('Header', b'value'), ('Other-Header', b'other')])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIHeaders))

    return suite

