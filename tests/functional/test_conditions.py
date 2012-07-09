import context
from hoboken import HobokenApplication, condition
from hoboken.conditions import *
from webob import Request
from nose.tools import *
from nose.exc import SkipTest


def test_useragent_condition():
    app = HobokenApplication("")

    @condition(user_agent("^Uagent1"))
    @app.get("/")
    def route_one(req, resp):
        return "one"

    @condition(user_agent("^Uagent2"))
    @app.get("/")
    def route_two(req, resp):
        return "two"

    req = Request.blank('/')
    req.headers['User-Agent'] = 'Uagent1 v1.2.3'
    resp = req.get_response(app)

    assert_equal(resp.status_int, 200)
    assert_equal(resp.body, 'one')

    req = Request.blank('/')
    req.headers['User-Agent'] = 'Uagent2 v1.2.3'
    resp = req.get_response(app)

    assert_equal(resp.status_int, 200)
    assert_equal(resp.body, 'two')


def test_host_condition():
    app = HobokenApplication("")

    @condition(host("sub1.foobar.com"))
    @app.get('/')
    def sub1(req, resp):
        return 'sub1'

    @condition(host("sub2.foobar.com"))
    @app.get('/')
    def sub2(req, resp):
        return 'sub2'

    req = Request.blank('/')
    req.host = 'sub1.foobar.com'
    resp = req.get_response(app)

    assert_equal(resp.status_int, 200)
    assert_equal(resp.body, 'sub1')

    req = Request.blank('/')
    req.host = 'sub2.foobar.com'
    resp = req.get_response(app)

    assert_equal(resp.status_int, 200)
    assert_equal(resp.body, 'sub2')


class TestAcceptsCondition():
    def setUp(self):
        app = HobokenApplication("")

        @condition(accepts("text/html"))
        @app.get('/')
        def html(req, resp):
            return 'html'

        @condition(accepts("text/plain"))
        @app.get('/')
        def plain(req, resp):
            return 'plain'

        @condition(accepts("text/*"))
        @app.get("/")
        def text(req, resp):
            return 'text'

        self.app = app

    def my_call(self, mime):
        req = Request.blank('/')
        req.accept = mime
        return req.get_response(self.app)

    def my_check(self, mime, body):
        resp = self.my_call(mime)
        assert_equal(resp.status_int, 200, "Mime {0} should succeed ({1})".format(mime, resp.status_int))
        assert_equal(resp.body, body, "{0} != {1}".format(resp.body, body))

    def test_plain_accept(self):
        self.my_check("text/html", "html")

    def test_compound_accept(self):
        self.my_check("text/html; q=1, application/other; q=0.5", "html")

    def test_other_accept(self):
        self.my_check("text/plain", "plain")

    def test_general_match(self):
        raise SkipTest("Since webob won't match this mime type")
        self.my_check("text/otherfoo", "text")

