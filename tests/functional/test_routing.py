from .context import hoboken
HobokenApplication = hoboken.HobokenApplication

from webob import Request, Response
from nose.tools import *


# Some useful tests from Sinatra: https://github.com/sinatra/sinatra/blob/master/test/routing_test.rb


# Helper function.  Calls the given application, returns a tuple of
# (status_int, body)
def call_app(app, path='/'):
    req = Request.blank(path)
    resp = req.get_response(app)
    return resp.status_int, resp.body


def test_responds_to():
    def body_func(req, resp):
        return 'body'

    for meth in HobokenApplication.SUPPORTED_METHODS:
        app = HobokenApplication("test_" + meth)
        app.add_route(meth, "/", body_func)

        code, body = call_app(app)

        assert_equal(code, 200, meth + " should succeed")
        assert_equal(body, 'body', meth + " should have a body")


def test_does_not_respond_to():
    def body_func(req, resp):
        return 'successful request'

    for meth in hoboken.HobokenApplication.SUPPORTED_METHODS:
        app = hoboken.HobokenApplication("test_" + meth)
        app.add_route(meth, "/somelongpath", body_func)

        code, body = call_app(app, '/someotherpath')

        assert_equal(code, 404)
        assert_not_equal(body, "successful request")


def test_head_method():
    """TODO: assert that HEAD returns no body"""
    def body_func(req, resp):
        return 'some body'

    app = hoboken.HobokenApplication


def test_head_fallback():
    """TODO: assert that HEAD will call GET when there's no matching route"""
    pass


def test_invalid_route():
    """TODO: Test routes that don't match, in various interesting configurations"""
    pass
