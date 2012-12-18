# -*- coding: utf-8 -*-

from . import BaseTestCase, skip, parametrize, parameters
import os
import sys
import yaml
import unittest

from mock import Mock

from hoboken.objects.mixins.user_agent import *
from hoboken.six import binary_type, text_type


def _e(val):
    if val is None:
        return None

    if isinstance(val, text_type):
        return val.encode('latin-1')
    elif isinstance(val, binary_type):
        return val
    else:
        raise ValueError("Unknown type for encoding (%r)!" % (val,))


class TestParsers(BaseTestCase):
    def setup(self):
        self.d = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "ua_tests"
        )

    def assert_ua_results(self, results, expected):
        self.assert_equal(results.ua.family, _e(expected['family']))
        self.assert_equal(results.ua.major, _e(expected['major']))
        self.assert_equal(results.ua.minor, _e(expected['minor']))
        self.assert_equal(results.ua.patch, _e(expected['patch']))

    def assert_os_results(self, results, expected):
        self.assert_equal(results.os.family, _e(expected['family']))
        self.assert_equal(results.os.major, _e(expected['major']))
        self.assert_equal(results.os.minor, _e(expected['minor']))
        self.assert_equal(results.os.patch, _e(expected['patch']))

    def assert_device_results(self, results, expected):
        self.assert_equal(results.device, _e(expected['family']))

    def check_from_file(self, file, assert_func):
        with open(os.path.join(self.d, file), 'rb') as f:
            contents = yaml.load(f)

        for test_case in contents['test_cases']:
            ua_string = test_case['user_agent_string']

            # We skip JS tests, since our library is server-side only for now.
            if 'js_ua' in test_case:
                continue

            r = parser.parse_all(_e(ua_string))
            assert_func(r, test_case)

    def test_useragent_strings(self):
        self.check_from_file('test_user_agent_parser.yaml', self.assert_ua_results)

    def test_firefox_strings(self):
        self.check_from_file('firefox_user_agent_strings.yaml', self.assert_ua_results)

    def test_os_strings(self):
        self.check_from_file('test_user_agent_parser_os.yaml', self.assert_os_results)

    def test_additional_os(self):
        self.check_from_file('additional_os_tests.yaml', self.assert_os_results)

    def test_devices(self):
        self.check_from_file('test_device.yaml', self.assert_device_results)


class TestOSClass(BaseTestCase):
    def setup(self):
        self.o = OSClass(
            family=b"FooFamily",
            major=b'123',
            minor=b'456',
            patch=b'789',
            patch_minor=b'0'
        )

    def test_version_string(self):
        self.assert_equal(self.o.version_string, b'123.456.789.0')

    def test_str(self):
        self.assert_equal(self.o.full_string, b"FooFamily 123.456.789.0")

        s = OSClass(family=b"AnotherFam").full_string
        self.assert_equal(s, b"AnotherFam")


class TestFullResults(BaseTestCase):
    def setup(self):
        u = UAClass()
        class DummyOS(object):
            @property
            def full_string(self):
                return b'Oper'
        o = DummyOS()

        self.r = FullResults(ua=u, os=o, device=b'')

    def test_full_string(self):
        self.assert_equal(self.r.full_string, b'Other/Oper')

        self.r.os = None
        self.assert_equal(self.r.full_string, b'Other')


class TestUserAgentMixin(BaseTestCase):
    def setup(self):
        class Foo(object):
            headers = {}

        class MixedIn(WSGIUserAgentMixin, Foo):
            pass

        self.c = MixedIn()

    def test_with_None(self):
        self.assert_true(self.c.user_agent is None)

    def test_with_value(self):
        # Value chosen semi-randomly.
        self.c.headers[b'User-Agent'] = b'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.648.133 Chrome/10.0.648.133 Safari/534.16'

        ua = self.c.user_agent
        self.assert_equal(ua.family, b'Chromium')
        self.assert_equal(ua.major, b'10')
        self.assert_equal(ua.minor, b'0')
        self.assert_equal(ua.patch, b'648')

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParsers))
    suite.addTest(unittest.makeSuite(TestOSClass))
    suite.addTest(unittest.makeSuite(TestFullResults))
    suite.addTest(unittest.makeSuite(TestUserAgentMixin))

    return suite

