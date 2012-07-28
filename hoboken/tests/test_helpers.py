from . import HobokenTestCase, skip
from webob import Request
from hoboken import halt, pass_route, redirect
import unittest

class TestHaltHelper(HobokenTestCase):
    def after_setup(self):
        self.halt_code = None
        self.halt_body = None

        @self.app.before("/before/halt")
        def before_halt_func(req, resp):
            halt(code=self.halt_code, body=self.halt_body)

        @self.app.get("/halts")
        def halts(req, resp):
            halt(code=self.halt_code, body=self.halt_body)
            return 'bad'

        self.app.debug = True

    def assert_halts_with(self, code, body, *args, **kwargs):
        """Helper function to set the halt value and assert"""
        self.halt_code = code
        self.halt_body = body
        self.assert_body_is(body, *args, **kwargs)

    def test_before_can_halt(self):
        self.assert_halts_with(200, 'foobar', path='/before/halt')

    def test_body_can_halt(self):
        self.assert_halts_with(200, 'good', path='/halts')


class TestPassHelper(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/aroute/*")
        def pass_one(req, resp):
            pass_route()
            return 'bad'

        @self.app.get("/aroute/*")
        def real_route(req, resp):
            return 'good'

        @self.app.before("/pass/before")
        def pass_before(req, resp):
            pass_route()
            resp.body = 'bad'

        @self.app.before("/pass/*")
        def before_pass_all(req, resp):
            resp.body += 'good'

        @self.app.get("/pass/*")
        def pass_before_route(req, resp):
            resp.body += 'foo'

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
        def upload(req, resp):
            # Upload stuff here.
            redirect(req, "/uploaded")

        @self.app.get("/uploaded")
        def uploaded(req, resp):
            return 'uploaded successfully'

        @self.app.get("/redirect")
        def redirect_func(req, resp):
            redirect(req, '/foo', status_code=self.redirect_code)

        self.app.debug = True

    def test_redirect(self):
        req = Request.blank("/upload", method='POST')
        resp = req.get_response(self.app)

        self.assert_equal(resp.status_int, 302)
        self.assert_equal(resp.location, 'http://localhost/uploaded')

    def test_redirect_code(self):
        for code in [301, 302, 303]:
            self.redirect_code = code

            req = Request.blank("/redirect")
            resp = req.get_response(self.app)

            self.assert_equal(resp.status_int, code)
            self.assert_equal(resp.location, 'http://localhost/foo')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHaltHelper))
    suite.addTest(unittest.makeSuite(TestPassHelper))
    suite.addTest(unittest.makeSuite(TestRedirectHelper))

    return suite

