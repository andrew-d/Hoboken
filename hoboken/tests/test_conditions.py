from . import HobokenTestCase
from hoboken import condition
from hoboken.six import u
from hoboken.conditions import *

from hoboken.tests.compat import unittest
from mock import Mock


class TestUserAgentCondition(HobokenTestCase):
    def after_setup(self):
        @condition(user_agent(b"^Uagent1"))
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

    def call_ua_condition(self, kwargs, ua_vals={}, os_vals={}, device=None):
        req = Mock()
        for k, v in ua_vals.items():
            setattr(req.user_agent, k, v)

        for k, v in os_vals.items():
            setattr(req.user_agent.os, k, v)

        if device is not None:
            req.user_agent.device = device

        func = user_agent(**kwargs)
        return func(req)

    def test_ua_conditions(self):
        ua_vals = {
            'family': 'a',
            'major':  'b',
            'minor':  'c',
            'patch':  'd',
        }

        # Unicode-encode one of the values to test.
        ua_vals['family'] = u(ua_vals['family'])

        self.assertTrue(self.call_ua_condition(ua_vals, ua_vals=ua_vals))

    def test_os_conditions(self):
        os_vals = {
            'family': 'a',
            'major':  'b',
            'minor':  'c',
            'patch':  'd',
        }
        kwargs = {}
        for k, v in os_vals.items():
            kwargs['os_' + k] = v

        # Unicode-encode one of the values to test.
        kwargs['os_family'] = u(kwargs['os_family'])

        self.assertTrue(self.call_ua_condition(kwargs, os_vals=os_vals))

    def test_failing_ua_condition(self):
        ua_vals = {
            'family': 'a',
            'major':  'b',
            'minor':  'c',
            'patch':  'd',
        }
        kwargs = {
            'family': 'a',
            'major':  'b',
            'minor':  'c',
            'patch':  'd',
        }

        self.assertTrue(self.call_ua_condition(kwargs, ua_vals=ua_vals))
        kwargs['minor'] = 'Q'
        self.assertFalse(self.call_ua_condition(kwargs, ua_vals=ua_vals))

    def test_failing_os_condition(self):
        os_vals = {
            'family': 'a',
            'major':  'b',
            'minor':  'c',
            'patch':  'd',
        }
        kwargs = {
            'os_family': 'a',
            'os_major':  'b',
            'os_minor':  'c',
            'os_patch':  'd',
        }

        self.assertTrue(self.call_ua_condition(kwargs, os_vals=os_vals))
        kwargs['os_minor'] = 'Q'
        self.assertFalse(self.call_ua_condition(kwargs, os_vals=os_vals))

    def test_device(self):
        self.assertTrue(self.call_ua_condition(
            {'device': 'aDevice'},
           device='aDevice')
        )

    def test_device_failing(self):
        self.assertFalse(self.call_ua_condition(
            {'device': 'aDevice'},
           device='anotherDevice')
        )

    def test_with_extra_kwargs(self):
        with self.assertRaises(TypeError):
            user_agent(foo='bar')


class TestHostCondition(HobokenTestCase):
    def after_setup(self):
        @condition(host(b"sub1.foobar.com"))
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

        @condition(accepts(b"text/html"))
        @self.app.get('/')
        def html():
            return 'html'

        @condition(accepts(b"text/plain"))
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

