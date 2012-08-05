# -*- coding: utf-8 -*-

from . import HobokenTestCase
from ..application import Request, Response
import unittest


class TestRequest(HobokenTestCase):
    def test_is_safe(self):
        for method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            r = Request.blank("/", method=method)
            self.assert_true(r.is_safe)

    def test_is_idempotent(self):
        for method in ['PUT', 'DELETE']:
            r = Request.blank("/", method=method)
            self.assert_true(r.is_idempotent)


class TestResponse(HobokenTestCase):
    def test_is_informational(self):
        e = Response(status_int=100)
        self.assert_true(e.is_informational)

    def test_is_success(self):
        e = Response(status_int=200)
        self.assert_true(e.is_success)

    def test_is_redirect(self):
        e = Response(status_int=300)
        self.assert_true(e.is_redirect)

    def test_is_client_error(self):
        e = Response(status_int=400)
        self.assert_true(e.is_client_error)

    def test_is_server_error(self):
        e = Response(status_int=500)
        self.assert_true(e.is_server_error)

    def test_is_not_found(self):
        e = Response(status_int=404)
        self.assert_true(e.is_not_found)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRequest))
    suite.addTest(unittest.makeSuite(TestResponse))

    return suite
