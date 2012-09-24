# -*- coding: utf-8 -*-

from . import HobokenTestCase, is_python3
from .. import HobokenApplication, condition
from ..application import HobokenBaseApplication, Route, halt, pass_route
from ..matchers import RegexMatcher
from ..exceptions import *
import os
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
            halt(code=self.halt_code, body=self.halt_body)

        @self.app.get("/halts")
        def halts():
            halt(code=self.halt_code, body=self.halt_body)
            return 'bad'

        self.app.config.debug = True

    def assert_halts_with(self, code, body, path):
        """Helper function to set the halt value and assert"""
        self.halt_code = code
        self.halt_body = body
        req = Request.blank(path)
        resp = req.get_response(self.app)
        self.assert_equal(resp.status_int, 200)
        self.assert_equal(resp.body, body)

    def test_before_can_halt(self):
        self.assert_halts_with(200, b'foobar', '/before/halt')

    def test_body_can_halt(self):
        self.assert_halts_with(200, b'good', '/halts')


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

        self.app.config.debug = True

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
            self.app.redirect('/foo', code=self.redirect_code)

        self.app.config.debug = True

    def test_redirect(self):
        req = Request.blank("/upload", method='POST')
        resp = req.get_response(self.app)

        self.assert_equal(resp.status_int, 302)
        self.assert_true(resp.location.endswith('/uploaded'))

    def test_redirect_code(self):
        for code in [301, 302, 303]:
            self.redirect_code = code

            req = Request.blank("/redirect")
            resp = req.get_response(self.app)

            self.assert_equal(resp.status_int, code)
            self.assert_true(resp.location.endswith('/foo'))

    def test_redirect_with_non_get(self):
        req = Request.blank("/upload", method='POST')
        req.http_version = "HTTP/1.1"
        resp = req.get_response(self.app)

        self.assert_equal(resp.status_int, 303)
        self.assert_true(resp.location.endswith('/uploaded'))


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


class TestMiscellaneousMethods(HobokenTestCase):
    def test_add_route_will_throw(self):
        with self.assert_raises(HobokenException):
            self.app.add_route('bad', None, None)

    def test_invalid_matcher_type(self):
        with self.assert_raises(InvalidMatchTypeException):
            @self.app.get(123)
            def bad():
                pass

    def test_find_route_will_return_none_on_failure(self):
        def not_exist():
            pass

        res = self.app.find_route(not_exist)
        self.assert_true(res is None)

    def test_url_for_will_return_none_on_failure(self):
        def not_a_route():
            pass

        url = self.app.url_for(not_a_route)
        self.assert_true(url is None)

    def test_only_one_route_per_function(self):
        with self.assert_raises(RouteExistsException):
            @self.app.get("/one")
            @self.app.get("/two")
            def route_func():
                pass

    def test_invalid_method(self):
        @self.app.get("/")
        def index():
            return b'foo'

        r = Request.blank("/")
        r.method = 'OTHER'
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_code, 405)

    def test_will_error_on_invalid_body(self):
        req = mock.MagicMock()
        resp = mock.MagicMock()
        value = 123

        with self.assert_raises(ValueError):
            self.app.on_returned_body(req, resp, value)

class TestConfig(HobokenTestCase):
    def test_can_get_set_values(self):
        self.app.config.foo = 'asdf'
        self.assert_equal(self.app.config.foo, 'asdf')
        self.assert_equal(self.app.config['foo'], 'asdf')

    def test_can_delete_values(self):
        self.app.config.foo = 'bar'
        del self.app.config.foo

        self.assert_true('foo' not in self.app.config)

    def test_will_fill_missing_views_dir(self):
        app = HobokenApplication('', root_directory='foo')
        expected_views = os.path.join('foo', 'views')
        self.assert_equal(app.config.views_directory, expected_views)

    def test_vars(self):
        app = HobokenApplication('')

        @app.get("/one")
        def one():
            app.vars.foo = 'bar'

        @app.get("/two")
        def two():
            self.assert_true('foo' not in app.vars)

        r = Request.blank("/one")
        resp = r.get_response(app)

        self.assert_true('foo' not in app.vars)

        r = Request.blank("/two")
        resp = r.get_response(app)


class TestInheritance(HobokenTestCase):
    def test_mixin_init_called(self):
        calls = []

        class Mixin(object):
            def __init__(self, *args, **kwargs):
                calls.append("mixin")
                super(Mixin, self).__init__(*args, **kwargs)

        class Inherited(HobokenBaseApplication, Mixin):
            def __init__(self, *args, **kwargs):
                calls.append("inherited")
                super(Inherited, self).__init__(*args, **kwargs)

        cls = Inherited("foobar")

        self.assert_true("inherited" in calls)
        self.assert_true("mixin" in calls)


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
    suite.addTest(unittest.makeSuite(TestMiscellaneousMethods))
    suite.addTest(unittest.makeSuite(TestConfig))
    suite.addTest(unittest.makeSuite(TestInheritance))

    return suite

