# -*- coding: utf-8 -*-

from . import HobokenTestCase
from ..application import Request, Response
from hoboken.tests.compat import unittest


class TestRequest(HobokenTestCase):
    def test_is_safe(self):
        for method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']:
            r = Request.build("/", method=method)
            self.assertTrue(r.is_safe)

    def test_is_idempotent(self):
        for method in ['PUT', 'DELETE']:
            r = Request.build("/", method=method)
            self.assertTrue(r.is_idempotent)


class TestResponse(HobokenTestCase):
    def test_is_informational(self):
        e = Response(status_int=100)
        self.assertTrue(e.is_informational)

    def test_is_success(self):
        e = Response(status_int=200)
        self.assertTrue(e.is_success)

    def test_is_redirect(self):
        e = Response(status_int=300)
        self.assertTrue(e.is_redirect)

    def test_is_client_error(self):
        e = Response(status_int=400)
        self.assertTrue(e.is_client_error)

    def test_is_server_error(self):
        e = Response(status_int=500)
        self.assertTrue(e.is_server_error)

    def test_is_not_found(self):
        e = Response(status_int=404)
        self.assertTrue(e.is_not_found)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRequest))
    suite.addTest(unittest.makeSuite(TestResponse))

    return suite
