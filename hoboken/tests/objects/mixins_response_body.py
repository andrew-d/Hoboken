# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.response_body import *
from hoboken.six import u

class TestIteratorFile(BaseTestCase):
    def setup(self):
        self.it = [b'one', b'two', b'three']
        self.f = IteratorFile(self.it)

    def test_readall(self):
        self.assert_equal(self.f.readall(), b'onetwothree')

    def test_simple(self):
        self.assert_equal(self.f.read(), b'onetwothree')

    def test_multiple_reads(self):
        self.assert_equal(self.f.read(3), b'one')
        self.assert_equal(self.f.read(), b'twothree')

    def test_partial_read(self):
        self.assert_equal(self.f.read(2), b'on')
        self.assert_equal(self.f.read(1), b'e')

        self.assert_equal(self.f.read(4), b'twot')
        self.assert_equal(self.f.read(4), b'hree')

    def test_read_beyond_end(self):
        self.assert_equal(self.f.read(), b'onetwothree')
        self.assert_equal(self.f.read(), b'')
        self.assert_equal(self.f.read(1), b'')

    def test_read_larger_than_size(self):
        self.assert_equal(self.f.read(999), b'onetwothree')

    def test_closed(self):
        self.f.read()
        self.assert_true(self.f.closed)

    def test_closed_readonly(self):
        with self.assert_raises(AttributeError):
            self.f.closed = True


class TestResponseBodyMixin(BaseTestCase):
    def setup(self):
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
        self.assert_equal(self.m.response_iter, [b''])

    def test_response_iter_set_bytes(self):
        self.m.response_iter = b'foobar'
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_response_iter_set_else(self):
        self.m.response_iter = [b'foobar']
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_set_filelike(self):
        b = BytesIO(b'foobar')
        self.m.body_file = b
        self.assert_equal(self.m.response_iter, [b'foobar'])

        b = BytesIO(b'foobar')
        self.m.body_file = b
        self.assert_equal(self.m.body_file.read(), b'foobar')

    def test_get_filelike(self):
        self.m.response_iter = [b'foobar']
        f = self.m.body_file
        self.assert_equal(f.read(), b'foobar')

    def test_set_body(self):
        self.m.body = b'foobar'
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_set_body_with_invalid(self):
        with self.assert_raises(ValueError):
            self.m.body = u('foo')

    def test_get_body(self):
        self.m.response_iter = [b'foo', b'bar']
        self.assert_equal(self.m.body, b'foobar')

    def test_set_text(self):
        self.m.text = u('foobar')
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_set_text_with_invalid(self):
        with self.assert_raises(ValueError):
            self.m.text = b'foo'

    def test_get_text(self):
        self.m.response_iter = [b'foo', b'bar']
        self.assert_equal(self.m.text, u('foobar'))



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResponseBodyMixin))
    suite.addTest(unittest.makeSuite(TestIteratorFile))

    return suite

