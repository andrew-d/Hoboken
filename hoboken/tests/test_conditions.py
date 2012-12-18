from . import HobokenTestCase
from hoboken import condition
from hoboken.six import u
from hoboken.conditions import *

import unittest
import pytest


class TestUserAgentCondition(HobokenTestCase):
    def after_setup(self):
        @condition(user_agent("^Uagent1"))
        @self.app.get("/")
        def route_one():
            return "one"

        @condition(user_agent(u("^Uagent2")))
        @self.app.get("/")
        def route_two():
            return "two"

    def test_useragent_one(self):
        self.assert_body_is("one", user_agent='Uagent1 v1.2.3')

    def test_useragent_two(self):
        self.assert_body_is("two", user_agent='Uagent2 v4.5.6')


class TestHostCondition(HobokenTestCase):
    def after_setup(self):
        @condition(host("sub1.foobar.com"))
        @self.app.get('/')
        def sub1():
            return 'sub1'

        @condition(host(u("sub2.foobar.com")))
        @self.app.get('/')
        def sub2():
            return 'sub2'

    def test_host1(self):
        self.assert_body_is("sub1", host='sub1.foobar.com')

    def test_host2(self):
        self.assert_body_is("sub2", host='sub2.foobar.com')


class TestAcceptsCondition(HobokenTestCase):
    def after_setup(self):
        self.app.config.debug = True

        @condition(accepts("text/html"))
        @self.app.get('/')
        def html():
            return 'html'

        @condition(accepts("text/plain"))
        @self.app.get('/')
        def plain():
            return 'plain'

        @condition(accepts(b"text/*".decode('latin-1')))
        @self.app.get("/")
        def text():
            return 'text'

        @condition(accepts(["application/json", "application/xml"]))
        @self.app.get("/two")
        def accepts_two():
            return 'two'

        self.app.config.debug = True

    def test_plain_accept(self):
        self.assert_body_is("html", accepts="text/html")

    def test_compound_accept(self):
        self.assert_body_is("html", accepts="text/html; q=1, application/other; q=0.5")

    def test_other_accept(self):
        self.assert_body_is("plain", accepts="text/plain")

    def test_general_match(self):
        self.assert_body_is("text", accepts="text/otherfoo")

    def test_list_of_accepts(self):
        self.assert_body_is("two", path="/two", accepts="application/json")
        self.assert_body_is("two", path="/two", accepts="application/xml")


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestUserAgentCondition))
    suite.addTest(unittest.makeSuite(TestHostCondition))
    suite.addTest(unittest.makeSuite(TestAcceptsCondition))

    return suite

