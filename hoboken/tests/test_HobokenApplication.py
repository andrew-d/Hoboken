# -*- coding: utf-8 -*-

from . import HobokenTestCase
from .. import HobokenApplication, condition
from ..application import Route, halt, pass_route
from ..matchers import RegexMatcher
import re
import sys
import unittest
from webob import Request
import mock


class TestHasHTTPMethods(HobokenTestCase):
    def test_has_all_methods(self):
        for x in self.app.SUPPORTED_METHODS:
            assert hasattr(self.app, x.lower())


class TestWorksWithConditions(HobokenTestCase):
    def after_setup(self):
        self.calls = []

        def cond_above(req):
            self.calls.append("above")
            return True

        def cond_below(req):
            self.calls.append("below")
            return True

        @condition(cond_above)
        @self.app.get('/')
        @condition(cond_below)
        def route_func():
            self.calls.append("body")
            return 'success'

    def test_condtions_order(self):
        self.assert_body_is("success")
        self.assert_equal(self.calls, ["below", "above", "body"])


class TestConditionCanAbortRequest(HobokenTestCase):
    def after_setup(self):
        def no_foo_in_path(req):
            return req.path.find('foo') == -1

        @condition(no_foo_in_path)
        @self.app.get('/:param')
        def bar(param=None):
            return param

    def test_should_work(self):
        self.assert_body_is("works", path='/works')

    def test_should_not_work(self):
        self.assert_not_found(path='/foobreaks')


class TestSubapps(HobokenTestCase):
    def after_setup(self):
        subapp = HobokenApplication("subapp")
        self.app.set_subapp(subapp)

        @subapp.get("/subapp")
        def subapp_func():
            return "subapp"

        @self.app.get("/app")
        def app_func():
            return "app"

    def test_app_call_works(self):
        self.assert_body_is("app", path='/app')

    def test_subapp_delegation_works(self):
        self.assert_body_is("subapp", path='/subapp')

    def test_neither(self):
        self.assert_not_found(path='/neither')


class TestHandlesExceptions(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/errors")
        def errorme():
            raise Exception("foobar bloo blah")

    def test_exception_handling(self):
        code, body = self.call_app(path='/errors')
        self.assert_equal(code, 500)


class TestBodyReturnValues(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/bytes")
        def bytes():
            return b'byte string'

        @self.app.get("/string")
        def string():
            # føø
            return b'f\xc3\xb8\xc3\xb8'.decode('utf-8')

    def test_bytes(self):
        req = Request.blank('/bytes')
        resp = req.get_response(self.app)
        self.assert_equal(resp.body, b'byte string')

    def test_bytes(self):
        req = Request.blank('/string')
        resp = req.get_response(self.app)
        self.assert_equal(resp.text, b'f\xc3\xb8\xc3\xb8'.decode('utf-8'))


class TestHaltHelper(HobokenTestCase):
    def after_setup(self):
        self.halt_code = None
        self.halt_body = None

        @self.app.before("/before/halt")
        def before_halt_func():
            halt(code=self.halt_code, text=self.halt_body)

        @self.app.get("/halts")
        def halts():
            halt(code=self.halt_code, text=self.halt_body)
            return 'bad'

        self.app.debug = True

    def assert_halts_with(self, code, body, *args, **kwargs):
        """Helper function to set the halt value and assert"""
        self.halt_code = code

        # The 'text' attribute of a webob Request only supports unicode
        # strings on Python 2.X, so we need to make this unicode.
        if sys.version_info[0] < 3:
            self.halt_body = unicode(body)
        else:
            self.halt_body = body

        self.assert_body_is(body, *args, **kwargs)

    def test_before_can_halt(self):
        self.assert_halts_with(200, 'foobar', path='/before/halt')

    def test_body_can_halt(self):
        self.assert_halts_with(200, 'good', path='/halts')


class TestPassHelper(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/aroute/*")
        def pass_one(splat):
            pass_route()
            return 'bad'

        @self.app.get("/aroute/*")
        def real_route(splat):
            return 'good'

        @self.app.before("/pass/before")
        def pass_before():
            pass_route()
            self.app.response.text = 'bad'

        @self.app.before("/pass/*")
        def before_pass_all(splat):
            self.app.response.text += 'good'

        @self.app.get("/pass/*")
        def pass_before_route(splat):
            self.app.response.text += 'foo'

        self.app.debug = True

    def test_pass_route(self):
        self.assert_body_is('good', path='/aroute/')

    def test_pass_before(self):
        # Passing in filter will simply jump to the next filter.  It has no
        # effect on the actual body routes themselves.
        self.assert_body_is('goodfoo', path='/pass/before')
        self.assert_body_is('goodfoo', path='/pass/other')


class TestRedirectHelper(HobokenTestCase):
    def after_setup(self):
        self.redirect_code = 0

        @self.app.post("/upload")
        def upload():
            # Upload stuff here.
            self.app.redirect("/uploaded")

        @self.app.get("/uploaded")
        def uploaded():
            return 'uploaded successfully'

        @self.app.get("/redirect")
        def redirect_func():
            self.app.redirect('/foo', status_code=self.redirect_code)

        self.app.debug = True

    def test_redirect(self):
        req = Request.blank("/upload", method='POST')
        resp = req.get_response(self.app)

        self.assert_equal(resp.status_int, 302)
        self.assert_equal(resp.location, 'http://localhost/uploaded')

    def test_redirect_code(self):
        for code in [301, 302, 303]:
            self.redirect_code = code

            req = Request.blank("/redirect")
            resp = req.get_response(self.app)

            self.assert_equal(resp.status_int, code)
            self.assert_equal(resp.location, 'http://localhost/foo')


class TestRoute(HobokenTestCase):
    def test_route_uppercases_method(self):
        m = Route(None, None)
        m.method = 'get'
        self.assert_equal(m.method, 'GET')


class TestMatcherTypes(HobokenTestCase):
    def test_will_handle_regex(self):
        r = re.compile("(.*?)")
        @self.app.get(r)
        def regex_get():
            return b'body'

        route = self.app.find_route(regex_get)
        self.assert_true(isinstance(route.matcher, RegexMatcher))

    def test_will_handle_regex_named_captures(self):
        r = re.compile("/(.*?)foo(?P<name>.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg, name=None):
            self.assert_equal(arg, 'ONE')
            self.assert_equal(name, 'TWO')
            return b'param'

        r = Request.blank("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'param')

    def test_will_handle_regex_named_captures_2(self):
        r = re.compile("/(?P<first>.*?)foo(?P<second>.*?)bar")

        @self.app.get(r)
        def regex_get_params(first=None, second=None):
            self.assert_equal(first, 'ONE')
            self.assert_equal(second, 'TWO')
            return b'param'

        r = Request.blank("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'param')

    def test_will_handle_regex_named_captures_3(self):
        r = re.compile("/(.*?)foo(.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg1, arg2):
            self.assert_equal(arg1, 'ONE')
            self.assert_equal(arg2, 'TWO')
            return b'param'

        r = Request.blank("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'param')

    def test_will_handle_regex_named_captures_4(self):
        r = re.compile("/(?P<first>.*?)foo(.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg, first=None):
            self.assert_equal(first, 'ONE')
            self.assert_equal(arg, 'TWO')
            return b'param'

        r = Request.blank("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(resp.body, b'param')

    def test_will_handle_custom_matcher(self):
        m = mock.MagicMock()
        m.match.return_value = (True, ['arg'], {'val': 'kwarg'})

        @self.app.get(m)
        def custom_get(arg, val=None):
            self.assert_equal(arg, 'arg')
            self.assert_equal(val, 'kwarg')
            return b'body'

        r = Request.blank("/")
        resp = r.get_response(self.app)
        self.assert_equal(resp.status_code, 200)
        self.assert_equal(m.match.call_count, 1)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHasHTTPMethods))
    suite.addTest(unittest.makeSuite(TestWorksWithConditions))
    suite.addTest(unittest.makeSuite(TestConditionCanAbortRequest))
    suite.addTest(unittest.makeSuite(TestSubapps))
    suite.addTest(unittest.makeSuite(TestHandlesExceptions))
    suite.addTest(unittest.makeSuite(TestBodyReturnValues))
    suite.addTest(unittest.makeSuite(TestHaltHelper))
    suite.addTest(unittest.makeSuite(TestPassHelper))
    suite.addTest(unittest.makeSuite(TestRedirectHelper))
    suite.addTest(unittest.makeSuite(TestRoute))
    suite.addTest(unittest.makeSuite(TestMatcherTypes))

    return suite

