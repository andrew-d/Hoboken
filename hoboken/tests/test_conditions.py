from . import HobokenTestCase
from hoboken import condition
from hoboken.conditions import *

from unittest import skip


class TestUserAgentCondition(HobokenTestCase):
    def after_setup(self):
        @condition(user_agent("^Uagent1"))
        @self.app.get("/")
        def route_one(req, resp):
            return "one"

        @condition(user_agent("^Uagent2"))
        @self.app.get("/")
        def route_two(req, resp):
            return "two"

    def test_useragent_one(self):
        self.assert_body_is("one", user_agent='Uagent1 v1.2.3')

    def test_useragent_two(self):
        self.assert_body_is("two", user_agent='Uagent2 v4.5.6')


class TestHostCondition(HobokenTestCase):
    def after_setup(self):
        @condition(host("sub1.foobar.com"))
        @self.app.get('/')
        def sub1(req, resp):
            return 'sub1'

        @condition(host("sub2.foobar.com"))
        @self.app.get('/')
        def sub2(req, resp):
            return 'sub2'

    def test_host1(self):
        self.assert_body_is("sub1", host='sub1.foobar.com')

    def test_host2(self):
        self.assert_body_is("sub2", host='sub2.foobar.com')


class TestAcceptsCondition(HobokenTestCase):
    def after_setup(self):
        @condition(accepts("text/html"))
        @self.app.get('/')
        def html(req, resp):
            return 'html'

        @condition(accepts("text/plain"))
        @self.app.get('/')
        def plain(req, resp):
            return 'plain'

        @condition(accepts("text/*"))
        @self.app.get("/")
        def text(req, resp):
            return 'text'

    def test_plain_accept(self):
        self.assert_body_is("html", accepts="text/html")

    def test_compound_accept(self):
        self.assert_body_is("html", accepts="text/html; q=1, application/other; q=0.5")

    def test_other_accept(self):
        self.assert_body_is("plain", accepts="text/plain")

    @skip("Since webob won't match this mime type")
    def test_general_match(self):
        self.assert_body_is("text", "text/otherfoo")

