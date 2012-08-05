from . import HobokenTestCase, skip
import sys
import unittest
from datetime import datetime
from webob import Request


class TestLastModified(HobokenTestCase):
    def after_setup(self):
        self.time = datetime(year=2012, month=7, day=15)
        self.app.debug = True

        @self.app.get("/resource")
        def resource():
            self.app.check_last_modified(self.time)
            return b'resource value'

        @self.app.put("/resource")
        def resource():
            self.app.check_last_modified(self.time)
            return b'resource value'

        @self.app.get("/bad")
        def bad_date():
            self.app.check_last_modified(None)
            return b'foo'

    def test_has_last_modified(self):
        r = Request.blank("/resource")
        resp = r.get_response(self.app)
        self.assert_true(resp.last_modified is not None)

    def test_no_last_modified(self):
        r = Request.blank("/bad")
        resp = r.get_response(self.app)
        self.assert_true(resp.last_modified is None)

    def test_no_last_modified_if_etag(self):
        r = Request.blank("/resource")
        r.if_none_match = 'foobar'
        resp = r.get_response(self.app)
        self.assert_true(resp.last_modified is not None)

    def test_will_return_304_for_get(self):
        r = Request.blank("/resource")
        r.if_modified_since = datetime(year=2012, month=7, day=20)
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 304)
        self.assert_equal(resp.body, b'')

    def test_will_return_200_for_newer(self):
        r = Request.blank("/resource")
        r.if_modified_since = datetime(year=2012, month=7, day=1)
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'resource value')

    def test_if_unmodified_since(self):
        r = Request.blank("/resource", method='PUT')
        r.if_unmodified_since = datetime(year=2012, month=7, day=20)
        r.body = b'put this here'
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 200)

    def test_if_unmodified_since_precondition_fail(self):
        r = Request.blank("/resource", method='PUT')
        r.if_unmodified_since = datetime(year=2012, month=7, day=1)
        r.body = b'put this here'
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 412)


class TestETag(HobokenTestCase):
    def after_setup(self):
        self.etag = b'some etag'
        self.app.debug = True

        @self.app.get("/resource")
        def resource():
            self.app.check_etag(self.etag)
            return b'resource value'

        @self.app.put("/resource")
        def resource():
            self.app.check_etag(self.etag)
            return b'success'

    def test_etag(self):
        r = Request.blank("/resource")
        resp = r.get_response(self.app)
        self.assert_equal(resp.etag, self.etag)

    def test_etag_will_return_304_for_get(self):
        r = Request.blank("/resource")
        r.if_none_match = self.etag
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 304)

    def test_etag_will_return_200_for_no_match(self):
        r = Request.blank("/resource")
        r.if_none_match = self.etag + b'else'
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)

    def test_etag_will_return_200_for_correct_match(self):
        r = Request.blank("/resource", method='PUT')
        r.if_match = self.etag
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)

    def test_etag_will_return_412_for_incorrect_match(self):
        r = Request.blank("/resource", method='PUT')
        r.if_match = self.etag + b'fail'
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 412)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLastModified))

    return suite

