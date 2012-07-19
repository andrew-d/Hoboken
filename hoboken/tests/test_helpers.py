from . import HobokenTestCase
from hoboken import halt, pass_route, redirect
from unittest import skip

class TestHaltHelper(HobokenTestCase):
    def after_setup(self):
        self.halt_code = None
        self.halt_body = None

        @self.app.before("/before/halt")
        def before_halt_func(req, resp):
            halt(code=self.halt_code, body=self.halt_body)

        @self.app.get("/halts")
        def halts(req, resp):
            halt(code=200, body='good')
            return 'bad'

        self.app.debug = True

    def test_before_can_halt(self):
        self.halt_code = 200
        self.halt_body = 'foobar'
        self.assert_body_is('foobar', path='/before/halt')

    def test_body_can_halt(self):
        self.assert_body_is('good', path='/halts')


class TestPasstHelper(HobokenTestCase):
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
        pass
