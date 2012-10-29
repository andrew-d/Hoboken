# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.response import *

class TestWSGIBaseResponse(BaseTestCase):
    def setup(self):
        self.e = WSGIBaseResponse()

    def test_status_defaults_to_success(self):
        self.assert_equal(self.e.status_int, 200)

    def test_status_int(self):
        self.e.status_int = 300
        self.assert_equal(self.e.status_int, 300)

    def test_status_int_fails(self):
        with self.assert_raises(ValueError):
            self.e.status_int = 600

    def test_status_text(self):
        self.e.status_int = 200
        self.assert_equal(self.e.status_text, 'OK')

    def test_status(self):
        self.e.status_int = 200
        self.assert_equal(self.e.status, '200 OK')

    def test_status_setter(self):
        self.e.status = '301 Moved Permanently'
        self.assert_equal(self.e.status_int, 301)

    def test_headers(self):
        self.e.headers['Cache-Control'] = 'foo'
        self.assert_equal(self.e.headers['Cache-Control'], 'foo')

    def test_response_iter(self):
        self.e.response_iter = ['a', 'b', 'c']
        self.assert_equal(self.e.response_iter, ['a', 'b', 'c'])

    def test_response_iter_fails(self):
        with self.assert_raises(ValueError):
            self.e.response_iter = 123

    def test_will_close_iter(self):
        i = MagicMock()
        self.e.response_iter = i
        self.e.close()
        self.assert_true(i.close.called)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIBaseResponse))

    return suite
