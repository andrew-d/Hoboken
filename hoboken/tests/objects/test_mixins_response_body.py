# -*- coding: utf-8 -*-

from hoboken.tests.compat import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.response_body import *
from hoboken.six import u

class TestIteratorFile(unittest.TestCase):
    def setUp(self):
        self.it = [b'one', b'two', b'three']
        self.f = IteratorFile(self.it)

    def test_readall(self):
        self.assertEqual(self.f.readall(), b'onetwothree')

    def test_simple(self):
        self.assertEqual(self.f.read(), b'onetwothree')

    def test_multiple_reads(self):
        self.assertEqual(self.f.read(3), b'one')
        self.assertEqual(self.f.read(), b'twothree')

    def test_partial_read(self):
        self.assertEqual(self.f.read(2), b'on')
        self.assertEqual(self.f.read(1), b'e')

        self.assertEqual(self.f.read(4), b'twot')
        self.assertEqual(self.f.read(4), b'hree')

    def test_read_beyond_end(self):
        self.assertEqual(self.f.read(), b'onetwothree')
        self.assertEqual(self.f.read(), b'')
        self.assertEqual(self.f.read(1), b'')

    def test_read_larger_than_size(self):
        self.assertEqual(self.f.read(999), b'onetwothree')

    def test_closed(self):
        self.f.read()
        self.assertTrue(self.f.closed)

    def test_closed_readonly(self):
        with self.assertRaises(AttributeError):
            self.f.closed = True


class TestResponseBodyMixin(unittest.TestCase):
    def setUp(self):
        class TestObject(object):
            def __init__(self):
                self._response_iter = [b'']

            @property
            def response_iter(self):
                return self._response_iter

            @response_iter.setter
            def response_iter(self, val):
                self._response_iter = val

        class MixedIn(ResponseBodyMixin, TestObject):
            charset = 'utf-8'

        self.m = MixedIn()

    def test_response_iter_get(self):
        self.assertEqual(self.m.response_iter, [b''])

    def test_response_iter_set_bytes(self):
        self.m.response_iter = b'foobar'
        self.assertEqual(self.m.response_iter, [b'foobar'])

    def test_response_iter_set_else(self):
        self.m.response_iter = [b'foobar']
        self.assertEqual(self.m.response_iter, [b'foobar'])

    def test_set_filelike(self):
        b = BytesIO(b'foobar')
        self.m.body_file = b
        self.assertEqual(self.m.response_iter, [b'foobar'])

        b = BytesIO(b'foobar')
        self.m.body_file = b
        self.assertEqual(self.m.body_file.read(), b'foobar')

    def test_get_filelike(self):
        self.m.response_iter = [b'foobar']
        f = self.m.body_file
        self.assertEqual(f.read(), b'foobar')

    def test_set_body(self):
        self.m.body = b'foobar'
        self.assertEqual(self.m.response_iter, [b'foobar'])

    def test_set_body_with_invalid(self):
        with self.assertRaises(ValueError):
            self.m.body = u('foo')

    def test_get_body(self):
        self.m.response_iter = [b'foo', b'bar']
        self.assertEqual(self.m.body, b'foobar')

    def test_set_text(self):
        self.m.text = u('foobar')
        self.assertEqual(self.m.response_iter, [b'foobar'])

    def test_set_text_with_invalid(self):
        with self.assertRaises(ValueError):
            self.m.text = b'foo'

    def test_get_text(self):
        self.m.response_iter = [b'foo', b'bar']
        self.assertEqual(self.m.text, u('foobar'))



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResponseBodyMixin))
    suite.addTest(unittest.makeSuite(TestIteratorFile))

    return suite

