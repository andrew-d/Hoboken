# import context
# from hoboken import HobokenApplication, condition
# from hoboken.conditions import *
from .context import hoboken, call_app
HobokenApplication = hoboken.HobokenApplication

from webob import Request
from nose.tools import *
from nose.exc import SkipTest


class TestFilters():
    def setUp(self):
        app = HobokenApplication("test_filters")

        @app.before("/before/*")
        def before_filter(req, resp):
            self.calls.append("before")

        @app.get("/*")
        def route_func(req, resp):
            self.calls.append("body")
            return req.route_params['splat'][0]

        @app.after("/after/*")
        def after_filter(req, resp):
            self.calls.append("after")

        @app.before("/both/*")
        def both_before_filter(req, resp):
            self.calls.append("before")

        @app.after("/both/*")
        def both_after_filter(req, resp):
            self.calls.append("after")

        @app.after("/both_at_once/*")
        @app.before("/both_at_once/*")
        def both_at_once_filter(req, resp):
            self.calls.append("both_at_once")

        self.app = app
        self.calls = []


    def call_app(self, path):
        return call_app(self.app, path)


    def test_neither(self):
        code, body = self.call_app("/neither")
        assert_equal(code, 200)
        assert_equal(body, "neither")
        assert_equal(self.calls, ["body"])

    def test_before(self):
        code, body = self.call_app("/before/stuff")
        assert_equal(code, 200)
        assert_equal(body, "before/stuff")
        assert_equal(self.calls, ["before", "body"])

    def test_after(self):
        code, body = self.call_app("/after/stuff")
        assert_equal(code, 200)
        assert_equal(body, "after/stuff")
        assert_equal(self.calls, ["body", "after"])

    def test_both(self):
        code, body = self.call_app("/both/stuff")
        assert_equal(code, 200)
        assert_equal(body, "both/stuff")
        assert_equal(self.calls, ["before", "body", "after"])

    def test_both_at_once(self):
        code, body = self.call_app("/both_at_once/stuff")
        assert_equal(code, 200)
        assert_equal(body, "both_at_once/stuff")
        assert_equal(self.calls, ["both_at_once", "body", "both_at_once"])


def test_before_filter_can_modify_route():
    app = HobokenApplication("test_before_filter_can_modify_route")

    @app.before("/notmatched")
    def modify_route(req, resp):
        req.environ['PATH_INFO'] = "/matched"

    @app.get("/matched")
    def route_func(req, resp):
        return 'success'

    code, body = call_app(app, "/matched")
    assert_equal(code, 200, "Calling the matched route should work")
    assert_equal(body, 'success')

    code, body = call_app(app, "/notmatched")
    assert_equal(code, 200, "Calling the modified route should work")
    assert_equal(body, 'success')

