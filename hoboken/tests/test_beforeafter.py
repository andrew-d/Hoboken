from . import HobokenTestCase
import unittest
from unittest import skip

class TestFilters(HobokenTestCase):
    def after_setup(self):
        self.calls = []

        @self.app.before("/before/*")
        def before_filter(req, resp):
            self.calls.append("before")

        @self.app.get("/*")
        def route_func(req, resp):
            self.calls.append("body")
            return req.urlargs[0]

        @self.app.after("/after/*")
        def after_filter(req, resp):
            self.calls.append("after")

        @self.app.before("/both/*")
        def both_before_filter(req, resp):
            self.calls.append("before")

        @self.app.after("/both/*")
        def both_after_filter(req, resp):
            self.calls.append("after")

        @self.app.after("/both_at_once/*")
        @self.app.before("/both_at_once/*")
        def both_at_once_filter(req, resp):
            self.calls.append("both_at_once")

    def test_neither(self):
        self.assert_body_is("neither", path="/neither")
        self.assert_equal(self.calls, ["body"])

    def test_before(self):
        self.assert_body_is("before/stuff", path="/before/stuff")
        self.assert_equal(self.calls, ["before", "body"])

    def test_after(self):
        self.assert_body_is("after/stuff", path="/after/stuff")
        self.assert_equal(self.calls, ["body", "after"])

    def test_both(self):
        self.assert_body_is("both/stuff", path="/both/stuff")
        self.assert_equal(self.calls, ["before", "body", "after"])

    def test_both_at_once(self):
        self.assert_body_is("both_at_once/stuff", path="/both_at_once/stuff")
        self.assert_equal(self.calls, ["both_at_once", "body", "both_at_once"])


class TestFilterCanModifyRoute(HobokenTestCase):
    def after_setup(self):
        @self.app.before("/notmatched")
        def modify_route(req, resp):
            req.environ['PATH_INFO'] = "/matched"

        @self.app.get("/matched")
        def route_func(req, resp):
            return 'success'

    def test_matched_route(self):
        self.assert_body_is("success", path="/matched")

    def test_modified_route(self):
        self.assert_body_is("success", path="/notmatched")


class TestFilterParams(HobokenTestCase):
    def after_setup(self):
        @self.app.before("/before/:param1/:param2/*")
        def before_func(req, resp):
            self.val = (req.urlvars['param1'] + '\n' +
                        req.urlvars['param2'] + '\n' +
                        req.urlargs[0])

        @self.app.after("/after/:foo/*/:bar")
        def after_func(req, resp):
            self.val = (req.urlvars['foo'] + '\n' +
                        req.urlargs[0] + '\n' +
                        req.urlvars['bar'])

        @self.app.get("/*")
        def catchall(req, resp):
            pass

        self.app.debug = True

    def test_before_params(self):
        self.call_app(path='/before/one/two/params')
        self.assert_equal(self.val, 'one\ntwo\nparams')

    def test_after_params(self):
        self.call_app(path='/after/abcd/morestuff/defg')
        self.assert_equal(self.val, 'abcd\nmorestuff\ndefg')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFilters))
    suite.addTest(unittest.makeSuite(TestFilterCanModifyRoute))
    suite.addTest(unittest.makeSuite(TestFilterParams))

    return suite

