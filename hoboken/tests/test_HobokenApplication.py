from . import HobokenTestCase
from ..application import HobokenApplication, condition
import unittest


class TestHasHTTPMethods(HobokenTestCase):
    def test_has_all_methods(self):
        for x in self.app.SUPPORTED_METHODS:
            assert hasattr(self.app, x.lower())

def test_is_wsgi_application():
    a = HobokenApplication("")
    # TODO: Mock WSGI environ and start_application, and test that they're
    # called properly when we make a WSGI request.  Maybe use WebOb to make
    # the request.


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
        def route_func(req, resp):
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
        def bar(req, resp):
            return req.urlvars['param']

    def test_should_work(self):
        self.assert_body_is("works", path='/works')

    def test_should_not_work(self):
        self.assert_not_found(path='/foobreaks')


class TestSubapps(HobokenTestCase):
    def after_setup(self):
        subapp = HobokenApplication("subapp")
        self.app.set_subapp(subapp)

        @subapp.get("/subapp")
        def subapp_func(req, resp):
            return "subapp"

        @self.app.get("/app")
        def app_func(req, resp):
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
        def errorme(req, resp):
            raise Exception("foobar bloo blah")

    def test_exception_handling(self):
        code, body = self.call_app(path='/errors')
        self.assert_equal(code, 500)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHasHTTPMethods))
    suite.addTest(unittest.makeSuite(TestWorksWithConditions))
    suite.addTest(unittest.makeSuite(TestConditionCanAbortRequest))
    suite.addTest(unittest.makeSuite(TestSubapps))
    suite.addTest(unittest.makeSuite(TestHandlesExceptions))

    return suite

