from __future__ import print_function

from . import HobokenTestCase, skip, skip_if, is_pypy
import os
import sys
import time
import unittest
import datetime
from webob import Request
from mock import patch, MagicMock


class TestLastModified(HobokenTestCase):
    def after_setup(self):
        self.time = datetime.datetime(year=2012, month=7, day=15)
        self.app.config.debug = True

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
        r.if_modified_since = datetime.datetime(year=2012, month=7, day=20)
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 304)
        self.assert_equal(resp.body, b'')

    def test_will_return_200_for_newer(self):
        r = Request.blank("/resource")
        r.if_modified_since = datetime.datetime(year=2012, month=7, day=1)
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'resource value')

    def test_if_unmodified_since(self):
        r = Request.blank("/resource", method='PUT')
        r.if_unmodified_since = datetime.datetime(year=2012, month=7, day=20)
        r.body = b'put this here'
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 200)

    def test_if_unmodified_since_precondition_fail(self):
        r = Request.blank("/resource", method='PUT')
        r.if_unmodified_since = datetime.datetime(year=2012, month=7, day=1)
        r.body = b'put this here'
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 412)


class TestETag(HobokenTestCase):
    def after_setup(self):
        self.etag = 'some etag'
        self.app.config.debug = True

        @self.app.get("/resource")
        def resource():
            self.app.check_etag(self.etag)
            return b'resource value'

        @self.app.put("/resource")
        def resource():
            self.app.check_etag(self.etag)
            return b'success'

    def call_app(self, path, *args, **kwargs):
        req = Request.blank(path, *args, **kwargs)
        resp = req.get_response(self.app)
        return resp

    def test_etag(self):
        resp = self.call_app("/resource")
        self.assert_equal(resp.etag, self.etag)

    def test_etag_will_return_304_for_correct_if_none_match(self):
        resp = self.call_app("/resource", if_none_match=self.etag)
        self.assert_equal(resp.status_code, 304)

    def test_etag_will_return_304_for_incorrect_if_none_match(self):
        resp = self.call_app("/resource", method='PUT', if_none_match=self.etag)
        self.assert_equal(resp.status_code, 412)

    def test_etag_will_return_200_for_no_if_none_match(self):
        resp = self.call_app("/resource", method='PUT', if_none_match=self.etag + 'false')
        self.assert_equal(resp.status_code, 200)

    def test_etag_will_return_200_for_correct_if_match(self):
        resp = self.call_app("/resource", method='PUT', if_match=self.etag)
        self.assert_equal(resp.status_code, 200)

    def test_etag_will_return_412_for_incorrect_if_match(self):
        resp = self.call_app("/resource", method='PUT', if_match=self.etag + 'fail')
        self.assert_equal(resp.status_code, 412)

    def test_wildcard_etag_if_match(self):
        resp = self.call_app("/resource", method='PUT', if_match='*')
        self.assert_equal(resp.status_code, 200)

    def test_wildcard_etag_if_none_match(self):
        resp = self.call_app("/resource", method='PUT', if_none_match='*')
        self.assert_equal(resp.status_code, 412)


class TestCacheControl(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/resource")
        def resource():
            self.app.set_cache_control(public=True, no_store=True)
            return b'resource'

    def call_app(self, path, *args, **kwargs):
        req = Request.blank(path, *args, **kwargs)
        resp = req.get_response(self.app)
        return resp

    def test_cache_control(self):
        resp = self.call_app('/resource')
        self.assert_true(resp.cache_control.public)
        self.assert_true(resp.cache_control.no_store)


class TestExpires(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/ccoffset")
        def resource():
            self.app.set_expires(10)
            return b'resource'

        @self.app.get("/ccabsolute")
        def resource():
            time = datetime.datetime(year=2012, month=7, day=15, hour=0, minute=1, second=0)
            self.app.set_expires(time)
            return b'resource'

        @self.app.get("/ccexpired")
        def resource():
            time = datetime.datetime(year=2012, month=7, day=15, hour=0, minute=0, second=0)
            self.app.set_expires(time)
            return b'resource'

    def call_app(self, path, *args, **kwargs):
        req = Request.blank(path, *args, **kwargs)
        resp = req.get_response(self.app)
        return resp

    @skip_if(is_pypy(), "Apparently mocking standard types doesn't work well on PyPy")
    def test_cache_control_with_offset(self):
        test_time = datetime.datetime(year=2012, month=7, day=15, hour=0, minute=0, second=0)
        with patch('datetime.datetime', wraps=datetime.datetime) as new_datetime:
            new_datetime.now.return_value = test_time
            resp = self.call_app("/ccoffset")

        # Note that webob assumes the input time is a UTC value, so we simply
        # remove the timezone info from the expires value to check it.
        expires_timestamp = time.mktime(resp.expires.replace(tzinfo=None).timetuple())
        test_timestamp = time.mktime(test_time.timetuple())
        self.assert_equal(expires_timestamp, test_timestamp + 10)
        self.assert_equal(resp.cache_control.max_age, 10)

    @skip_if(is_pypy(), "Apparently mocking standard types doesn't work well on PyPy")
    def test_cache_control_with_absolute(self):
        test_time = datetime.datetime(year=2012, month=7, day=15, hour=0, minute=0, second=0)
        with patch('datetime.datetime', wraps=datetime.datetime) as new_datetime:
            new_datetime.now.return_value = test_time
            resp = self.call_app("/ccabsolute")

        # Note that webob assumes the input time is a UTC value, so we simply
        # remove the timezone info from the expires value to check it.
        expires_timestamp = time.mktime(resp.expires.replace(tzinfo=None).timetuple())
        test_timestamp = time.mktime(test_time.timetuple())
        self.assert_equal(expires_timestamp, test_timestamp + 60)
        self.assert_equal(resp.cache_control.max_age, 60)

    @skip_if(is_pypy(), "Apparently mocking standard types doesn't work well on PyPy")
    def test_cache_control_already_expired(self):
        test_time = datetime.datetime(year=2012, month=7, day=15, hour=1, minute=0, second=0)
        with patch('datetime.datetime', wraps=datetime.datetime) as new_datetime:
            new_datetime.now.return_value = test_time
            resp = self.call_app("/ccexpired")

        self.assert_equal(resp.cache_control.max_age, 0)


class TestRedirection(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/redirect_back")
        def redirect():
            self.app.redirect_back()

        @self.app.get("/redirect_fail")
        def redirect_fail():
            self.assert_false(self.app.redirect_back())
            return b'no redirect'

        @self.app.get("/to_me")
        def target():
            return b'target'

        @self.app.get("/redirect_to")
        def redirect_to():
            self.app.redirect_to(target)

    def test_redirect_back_success(self):
        r = Request.blank("/redirect_back", referer='http://www.google.com')
        resp = r.get_response(self.app)

        self.assert_true(300 <= resp.status_int <= 399)
        self.assert_equal(resp.location, 'http://www.google.com')

    def test_redirect_back_failure(self):
        r = Request.blank("/redirect_fail", referer='')
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'no redirect')

    def test_redirect_to(self):
        r = Request.blank("/redirect_to")
        resp = r.get_response(self.app)

        self.assert_true(300 <= resp.status_int <= 399)
        self.assert_true(resp.location.endswith('/to_me'))


class TestShift(HobokenTestCase):
    def test_shift_will_render(self):
        curr_file = os.path.abspath(__file__)
        dir_name = os.path.dirname(curr_file)
        path = os.path.join(dir_name, "test_shift.bare")
        output = self.app.render(path)

        self.assert_true(output is not None)
        self.assert_equal(output.strip(), "This is a bare file.")

    def test_shift_will_fail_on_unknown(self):
        output = self.app.render("not_existing.badext")
        self.assert_true(output is None)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestLastModified))
    suite.addTest(unittest.makeSuite(TestETag))
    suite.addTest(unittest.makeSuite(TestCacheControl))
    suite.addTest(unittest.makeSuite(TestExpires))
    suite.addTest(unittest.makeSuite(TestRedirection))
    suite.addTest(unittest.makeSuite(TestShift))

    return suite

