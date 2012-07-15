from .context import hoboken
HobokenApplication = hoboken.HobokenApplication

from nose.tools import *
from webob import Request


# Helper function.  Calls the given application, returns a tuple of
# (status_int, body)
def call_app(app, path="/", method="GET"):
    req = Request.blank(path)
    req.method = method
    resp = req.get_response(app)
    return resp.status_int, resp.body


def test_has_http_methods():
    a = HobokenApplication("")
    for x in HobokenApplication.SUPPORTED_METHODS:
        assert hasattr(a, x.lower())


def test_is_wsgi_application():
    a = HobokenApplication("")
    # TODO: Mock WSGI environ and start_application, and test that they're
    # called properly when we make a WSGI request.  Maybe use WebOb to make
    # the request.

def test_works_with_conditions():
    calls = []

    def cond_above(req):
        calls.append("above")
        return True

    def cond_below(req):
        calls.append("below")
        return True

    app = HobokenApplication("test_works_with_conditions")

    @hoboken.condition(cond_above)
    @app.get('/')
    @hoboken.condition(cond_below)
    def route_func(req, resp):
        calls.append("body")
        return 'success'

    code, body = call_app(app)

    assert_equal(code, 200)
    assert_equal(calls, ["below", "above", "body"])


def test_condition_can_abort_request():
    app = HobokenApplication("test_condition_can_abort_request")

    def no_foo_in_path(req):
        return req.path.find('foo') == -1

    @hoboken.condition(no_foo_in_path)
    @app.get('/:param')
    def bar(req, resp):
        return req.route_params['param']

    code, body = call_app(app, '/works')

    assert_equal(code, 200)
    assert_equal(body, 'works')

    code, body = call_app(app, '/foobreaks')

    assert_equal(code, 404)


def test_app_passes_to_subapp():
    subapp = HobokenApplication("subapp")
    app = HobokenApplication("app", sub_app=subapp)

    @subapp.get("/subapp")
    def subapp_func(req, resp):
        return "subapp"

    @app.get("/app")
    def app_func(req, resp):
        return "app"

    code, body = call_app(app, "/app")
    assert_equal(code, 200)
    assert_equal(body, "app")

    code, body = call_app(app, "/subapp")
    assert_equal(code, 200)
    assert_equal(body, "subapp")

    code, body = call_app(app, "/neither")
    assert_equal(code, 404)


def test_handles_exceptions():
    app = HobokenApplication("test_handes_exceptions")

    @app.get('/errors')
    def errorme(req, resp):
        raise Exception("foobar bloo blah")

    code, body = call_app(app, '/errors')

    assert_equal(code, 500)
