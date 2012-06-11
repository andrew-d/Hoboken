from .context import hoboken

from webob import Request, Response


# Some useful tests from Sinatra: https://github.com/sinatra/sinatra/blob/master/test/routing_test.rb


# Helper function.  Calls the given application, returns a tuple of
# (status_int, body)
def test_app(app, path='/'):
    req = Request.blank(path)
    resp = req.get_response(app)
    return resp.status_int, resp.body


def test_responds_to():
    def body_func(req, resp):
        return 'body'

    for meth in hoboken.HobokenApplication.SUPPORTED_METHODS:
        app = hoboken.HobokenApplication("test_" + meth)
        app.add_route(meth, "/", body_func)

        code, body = test_app(app)

        assert code == 200
        assert body == 'body'


def test_does_not_respond_to():
    def body_func(req, resp):
        return 'successful request'

    for meth in hoboken.HobokenApplication.SUPPORTED_METHODS:
        app = hoboken.HobokenApplication("test_" + meth)
        app.add_route(meth, "/somelongpath", body_func)

        code, body = test_app(app, '/someotherpath')

        assert code == 404
        assert body != "successful request"


def test_head_method():
    """TODO: assert that HEAD returns no body"""
    pass


def test_head_fallback():
    """TODO: assert that HEAD will call GET when there's no matching route"""
    pass


def test_invalid_route():
    """TODO: Test routes that don't match, in various interesting configurations"""
    pass
