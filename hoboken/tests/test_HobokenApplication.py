# -*- coding: utf-8 -*-

from __future__ import division
from . import HobokenTestCase
from .. import HobokenApplication, condition
from ..application import HobokenBaseApplication, Route, halt, pass_route
from ..matchers import RegexMatcher
from ..exceptions import *
import os
import re
import sys
import time
import threading
from hoboken.tests.compat import slow_test, unittest
import mock
from hoboken.application import Request, ConfigProperty
from hoboken.six import PY3


class TestHasHTTPMethods(HobokenTestCase):
    def test_has_all_methods(self):
        for x in self.app.SUPPORTED_METHODS:
            self.assertTrue(hasattr(self.app, x.lower()))


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
        self.assertEqual(self.calls, ["below", "above", "body"])


class TestConditionCanAbortRequest(HobokenTestCase):
    def after_setup(self):
        def no_foo_in_path(req):
            return req.path.find(b'foo') == -1

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

        @subapp.get("/subapp")
        def subapp_func():
            return "subapp"

        @self.app.get("/app")
        def app_func():
            return "app"

        # NOTE: order matters!
        @self.app.get("/*")
        def final_func(path):
            self.app.delegate(subapp)

    def test_app_call_works(self):
        self.assert_body_is("app", path='/app')

    def test_subapp_delegation_works(self):
        self.assert_body_is("subapp", path='/subapp')

    def test_neither(self):
        self.assert_not_found(path='/neither')

    def test_delegate_will_handle_none(self):
        self.assertFalse(self.app.delegate(None))


class TestHandlesExceptions(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/errors")
        def errorme():
            raise Exception("foobar bloo blah")

    def test_exception_handling(self):
        code, body = self.call_app(path='/errors')
        self.assertEqual(code, 500)


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
        req = Request.build('/bytes')
        resp = req.get_response(self.app)
        self.assertEqual(resp.body, b'byte string')

    def test_bytes(self):
        req = Request.build('/string')
        resp = req.get_response(self.app)
        self.assertEqual(resp.text, b'f\xc3\xb8\xc3\xb8'.decode('utf-8'))


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

        self.app.debug = True

    def assert_halts_with(self, code, body, path):
        """Helper function to set the halt value and assert"""
        self.halt_code = code
        self.halt_body = body
        req = Request.build(path)
        resp = req.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, body)

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
            self.app.response.body = b'bad'

        @self.app.before("/pass/*")
        def before_pass_all(splat):
            self.app.response.body += b'good'

        @self.app.get("/pass/*")
        def pass_before_route(splat):
            self.app.response.body += b'foo'

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
            self.app.redirect('/foo', code=self.redirect_code)

        self.app.debug = True

    def test_redirect(self):
        req = Request.build("/upload", method='POST')
        resp = req.get_response(self.app)

        self.assertEqual(resp.status_int, 302)
        self.assertTrue(resp.headers['Location'].endswith(b'/uploaded'))

    def test_redirect_code(self):
        for code in [301, 302, 303]:
            self.redirect_code = code

            req = Request.build("/redirect")
            resp = req.get_response(self.app)

            self.assertEqual(resp.status_int, code)
            self.assertTrue(resp.headers['Location'].endswith(b'/foo'))

    def test_redirect_with_non_get(self):
        req = Request.build("/upload", method='POST')
        req.http_version = "HTTP/1.1"
        resp = req.get_response(self.app)

        self.assertEqual(resp.status_int, 303)
        self.assertTrue(resp.headers['Location'].endswith(b'/uploaded'))


class TestRoute(HobokenTestCase):
    def test_route_uppercases_method(self):
        m = Route(None, None)
        m.method = 'get'
        self.assertEqual(m.method, 'GET')


class TestMatcherTypes(HobokenTestCase):
    def test_will_handle_regex(self):
        r = re.compile(b"(.*?)")

        @self.app.get(r)
        def regex_get():
            return b'body'

        route = self.app.find_route(regex_get)
        self.assertTrue(isinstance(route.matcher, RegexMatcher))

    def test_will_handle_regex_named_captures(self):
        r = re.compile(b"/(.*?)foo(?P<name>.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg, name=None):
            self.assertEqual(arg, b'ONE')
            self.assertEqual(name, b'TWO')
            return b'param'

        r = Request.build("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, b'param')

    def test_will_handle_regex_named_captures_2(self):
        r = re.compile(b"/(?P<first>.*?)foo(?P<second>.*?)bar")

        @self.app.get(r)
        def regex_get_params(first=None, second=None):
            self.assertEqual(first, b'ONE')
            self.assertEqual(second, b'TWO')
            return b'param'

        r = Request.build("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, b'param')

    def test_will_handle_regex_named_captures_3(self):
        r = re.compile(b"/(.*?)foo(.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg1, arg2):
            self.assertEqual(arg1, b'ONE')
            self.assertEqual(arg2, b'TWO')
            return b'param'

        r = Request.build("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, b'param')

    def test_will_handle_regex_named_captures_4(self):
        r = re.compile(b"/(?P<first>.*?)foo(.*?)bar")

        @self.app.get(r)
        def regex_get_params(arg, first=None):
            self.assertEqual(first, b'ONE')
            self.assertEqual(arg, b'TWO')
            return b'param'

        r = Request.build("/ONEfooTWObar")
        resp = r.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.body, b'param')

    def test_will_handle_custom_matcher(self):
        m = mock.MagicMock()
        m.match.return_value = (True, ['arg'], {'val': 'kwarg'})

        @self.app.get(m)
        def custom_get(arg, val=None):
            self.assertEqual(arg, 'arg')
            self.assertEqual(val, 'kwarg')
            return b'body'

        r = Request.build("/")
        resp = r.get_response(self.app)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(m.match.call_count, 1)


class TestMiscellaneousMethods(HobokenTestCase):
    def test_add_route_will_throw(self):
        with self.assertRaises(HobokenException):
            self.app.add_route('bad', None, None)

    def test_invalid_matcher_type(self):
        with self.assertRaises(InvalidMatchTypeException):
            @self.app.get(123)
            def bad():
                pass

    def test_find_route_will_return_none_on_failure(self):
        def not_exist():
            pass

        res = self.app.find_route(not_exist)
        self.assertIsNone(res)

    def test_url_for_will_return_none_on_failure(self):
        def not_a_route():
            pass

        url = self.app.url_for(not_a_route)
        self.assertIsNone(url)

    def test_only_one_route_per_function(self):
        with self.assertRaises(RouteExistsException):
            @self.app.get("/one")
            @self.app.get("/two")
            def route_func():
                pass

    def test_invalid_method(self):
        @self.app.get("/")
        def index():
            return b'foo'

        r = Request.build("/")
        r.method = 'OTHER'
        resp = r.get_response(self.app)

        self.assertEqual(resp.status_int, 405)

    def test_will_error_on_invalid_body(self):
        req = mock.MagicMock()
        resp = mock.MagicMock()
        value = 123

        with self.assertRaises(ValueError):
            self.app.on_returned_body(req, resp, value)

    def test_with_request_lock(self):
        self.app.config['SERIALIZE_REQUESTS'] = True

        @self.app.get('/')
        def idx():
            return b'foo'

        @self.app.get('/errors')
        def err():
            raise RuntimeError('foobar')

        r = Request.build('/')
        e = r.get_response(self.app)
        self.assertEqual(e.status_int, 200)

        r = Request.build('/errors')
        e = r.get_response(self.app)
        self.assertEqual(e.status_int, 500)

    def test_threadlocals_from_other_threads(self):
        completed = [False, False, False]

        def test_func_getting():
            self.assertIsNone(self.app.request)
            self.assertIsNone(self.app.response)
            self.assertIsNotNone(self.app.g)
            completed[0] = True

        def test_func_setting():
            self.app.request = 1
            self.app.response = 2
            completed[1] = True

        def test_func_deleting():
            del self.app.request
            del self.app.response
            del self.app.g
            completed[2] = True

        self.app.g.foo = 123

        threads = [
            threading.Thread(target=test_func_getting),
            threading.Thread(target=test_func_setting),
            threading.Thread(target=test_func_deleting),
        ]
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # This checks that our above threads don't clobber this thread's
        # app.g object.
        self.assertEqual(self.app.g.foo, 123)

        for x in completed:
            self.assertTrue(x)


class TestConfig(HobokenTestCase):
    def test_can_get_set_values(self):
        self.app.config['FOO'] = 'asdf'
        self.assertEqual(self.app.config['FOO'], 'asdf')

    def test_can_delete_values(self):
        self.app.config['FOO'] = 'bar'
        del self.app.config['FOO']

        self.assertNotIn('FOO', self.app.config)

    def test_will_find_app_file(self):
        self.assertIn('APPLICATION_FILE', self.app.config)
        self.assertIsNotNone(self.app.config['APPLICATION_FILE'])

    def test_other_dirs_based_on_app_file(self):
        app_file = os.path.join('tmp', 'foo.py')
        a = HobokenApplication('', config={'APPLICATION_FILE': app_file})

        root = os.path.dirname(app_file)
        d1 = os.path.join(root, 'views')
        d2 = os.path.join(root, 'static')

        self.assertEqual(a.config['ROOT_DIRECTORY'], root)
        self.assertEqual(a.config['VIEWS_DIRECTORY'], d1)
        self.assertEqual(a.config['STATIC_DIRECTORY'], d2)

    def test_will_not_overwrite_provided_dirs(self):
        a = HobokenApplication('', config={
            'VIEWS_DIRECTORY': 'foobar',
            'STATIC_DIRECTORY': 'asdf',
        })

        self.assertEqual(a.config['VIEWS_DIRECTORY'], 'foobar')
        self.assertEqual(a.config['STATIC_DIRECTORY'], 'asdf')

    def test_property_will_return_obj(self):
        self.assertTrue(isinstance(HobokenApplication.debug, ConfigProperty))

    def test_g(self):
        app = HobokenApplication('')

        @app.get("/one")
        def one():
            app.g.foo = 'bar'

        @app.get("/two")
        def two():
            self.assertNotIn('foo', app.g)

        r = Request.build("/one")
        resp = r.get_response(app)

        self.assertNotIn('foo', app.g.__dict__)

        r = Request.build("/two")
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

        self.assertIn("inherited", calls)
        self.assertIn("mixin", calls)


class TestConsistency(unittest.TestCase):
    def setUp(self):
        self.ctr = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            val = self.ctr
            self.ctr += 1
            return val

    @slow_test
    def test_threading(self):
        app = HobokenApplication(__name__)

        @app.get("/num")
        def get_num():
            val = self.increment()
            return str(val)

        self._run_test(app)

    @slow_test
    def test_threading_with_request_lock(self):
        app = HobokenApplication(__name__)
        app.config['SERIALIZE_REQUESTS'] = True

        @app.get("/num")
        def get_num():
            # This is deliberately not thread-safe.   The time.sleep here
            # is to force a thread context-switch, which should result in
            # a failed result, without synchronization.
            val = self.ctr
            time.sleep(0.01)
            self.ctr += 1
            return str(val)

        # Note that this test is SLOW, due to the sleeping, context-switching,
        # and locks, so we only test with 200 requests/5 threads.
        self._run_test(app, num_requests=200, num_threads=5)

    def _run_test(self, app, num_requests=1000, num_threads=10, path='/num'):
        # Thread variables.
        responses = []

        # Thread target.
        def requestor_func():
            for i in range(0, num_requests // num_threads):
                resp = Request.build(path).get_response(app)
                responses.append(resp.body)

        # Start all threads
        threads = [threading.Thread(target=requestor_func) for i in range(num_threads)]
        for t in threads:
            t.start()

        # Wait on threads.
        for t in threads:
            t.join()

        # Assert length.
        self.assertEqual(len(responses), num_requests)

        # Helper function that converts for us.
        if PY3:
            convertor = lambda s: int(s.decode('latin-1'))
        else:
            convertor = lambda s: int(s)

        # Convert responses to integers, and then assert that we have the right values.
        sorted_list = sorted(convertor(s) for s in responses)
        for i, val in enumerate(sorted_list):
            self.assertEqual(val, i)


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

