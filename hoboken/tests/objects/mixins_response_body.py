# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.response_body import *

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
            pass

        self.m = MixedIn()

    def test_response_iter_get(self):
        self.assert_equal(self.m.response_iter, [b''])

    def test_response_iter_set_bytes(self):
        self.m.response_iter = b'foobar'
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_response_iter_set_filelike(self):
        b = BytesIO(b'foobar')
        self.m.response_iter = b
        self.assert_equal(self.m.response_iter, [b'foobar'])

    def test_response_iter_set_else(self):
        self.m.response_iter = [b'foobar']
        self.assert_equal(self.m.response_iter, [b'foobar'])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestResponseBodyMixin))

    return suite

