from .context import hoboken
HobokenApplication = hoboken.HobokenApplication

from nose.tools import *
from webob import Request


# Some useful tests from Sinatra: https://github.com/sinatra/sinatra/blob/master/test/routing_test.rb


# Helper function.  Calls the given application, returns a tuple of
# (status_int, body)
def call_app(app, path="/", method="GET"):
    req = Request.blank(path)
    req.method = method
    resp = req.get_response(app)
    return resp.status_int, resp.body


def body_func(req, resp):
    return "request body"


def test_responds_to():
    for meth in HobokenApplication.SUPPORTED_METHODS:
        app = HobokenApplication("test_" + meth)
        app.add_route(meth, "/", body_func)

        code, body = call_app(app, method=meth)

        assert_equal(code, 200, meth + " should succeed")

        if meth != "HEAD":
            assert_equal(body, "request body", meth + " should have a body")


def test_does_not_respond_to():
    for meth in hoboken.HobokenApplication.SUPPORTED_METHODS:
        app = hoboken.HobokenApplication("test_" + meth)
        app.add_route(meth, "/somelongpath", body_func)

        code, body = call_app(app, "/someotherpath")

        assert_equal(code, 404)
        assert_not_equal(body, "request body")


def test_head_method():
    """Assert that HEAD returns no body.  TODO: Set custom header"""
    app = HobokenApplication("test_head_no_body")
    app.add_route("HEAD", "/headpath", body_func)

    code, body = call_app(app, "/headpath", method="HEAD")

    assert_equal(code, 200)
    assert_equal(body, "", "Body should be empty for a HEAD request")


def test_head_fallback():
    """Assert that HEAD will call GET when there"s no matching route.  TODO: Set custom header"""
    app = HobokenApplication("test_head_fallback")
    app.add_route("GET", "/getpath", body_func)

    code, body = call_app(app, "/getpath", method="HEAD")

    assert_equal(code, 200, "App should fall back to GET for HEAD requests")
    assert_equal(body, "", "Body should be empty for a HEAD request")


def test_encoded_slashes():
    def echo_func(req, resp):
        return req.route_params['param']

    app = HobokenApplication("test_encoded_slashes")
    app.add_route("GET", "/:param", echo_func)

    code, body = call_app(app, "/foo%2Fbar")

    assert_equal(code, 200)
    assert_equal(body, "foo/bar")


def test_splat_params():
    def echo_func(req, resp):
        return '\n'.join(req.route_params['splat'])

    app = HobokenApplication("test_splat_params")
    app.add_route("GET", "/*/foo/*/*", echo_func)

    code, body = call_app(app, "/one/foo/two/three")

    assert_equal(code, 200)
    assert_equal(body, "one\ntwo\nthree")

    code, body = call_app(app, "/one/foo/two/three/four")

    assert_equal(code, 200)
    assert_equal(body, "one\ntwo\nthree/four")

    code, body = call_app(app, "/one/foo/two")

    assert_equal(code, 404)


def test_mixed_params():
    def test_func(req, resp):
        assert_equal(len(req.route_params["splat"]), 1)
        assert_equal(req.route_params["splat"][0], "foo/bar")
        assert_equal(req.route_params["one"], "two")

    app = HobokenApplication("test_mixed_params")
    app.add_route("GET", "/:one/*", test_func)

    code, body = call_app(app, "/two/foo/bar")

    assert_equal(code, 200)


def test_dot_in_param():
    def test_func(req, resp):
        return req.route_params["foo"]

    app = HobokenApplication("test_dot_in_param")
    app.add_route("GET", "/:foo/:bar", test_func)

    code, body = call_app(app, "/test@foo.com/john")

    assert_equal(code, 200)
    assert_equal(body, "test@foo.com")


def test_dot_outside_param():
    def test_func(req, resp):
        assert_equal(req.route_params["one"], "foo")
        assert_equal(req.route_params["two"], "bar")
        return "works"

    app = HobokenApplication("test_dot_outside_param")
    app.add_route("GET", "/:one.:two", test_func)

    code, body = call_app(app, "/foo.bar")

    assert_equal(code, 200)
    assert_equal(body, "works")

    code, body = call_app(app, "/foo1bar")

    assert_equal(code, 404)


# TODO: Tests involving $, +, ' ', and more . magic.
# More TODO: Tests involving various encodings of spaces (" ", %20, +)
#            Tests involving ampersands
#            Tests involving URL encoding

def test_invalid_route():
    """TODO: Test routes that don't match, in various interesting configurations"""
    pass
