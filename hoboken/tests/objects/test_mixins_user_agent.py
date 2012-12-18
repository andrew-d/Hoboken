# -*- coding: utf-8 -*-

import os
import sys
import yaml
import unittest

import pytest
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


class TestParsers(unittest.TestCase):
    def setUp(self):
        self.d = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "ua_tests"
        )

    def assert_ua_results(self, results, expected):
        self.assertEqual(results.ua.family, _e(expected['family']))
        self.assertEqual(results.ua.major, _e(expected['major']))
        self.assertEqual(results.ua.minor, _e(expected['minor']))
        self.assertEqual(results.ua.patch, _e(expected['patch']))

    def assert_os_results(self, results, expected):
        self.assertEqual(results.os.family, _e(expected['family']))
        self.assertEqual(results.os.major, _e(expected['major']))
        self.assertEqual(results.os.minor, _e(expected['minor']))
        self.assertEqual(results.os.patch, _e(expected['patch']))

    def assert_device_results(self, results, expected):
        self.assertEqual(results.device, _e(expected['family']))

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


class TestOSClass(unittest.TestCase):
    def setUp(self):
        self.o = OSClass(
            family=b"FooFamily",
            major=b'123',
            minor=b'456',
            patch=b'789',
            patch_minor=b'0'
        )

    def test_version_string(self):
        self.assertEqual(self.o.version_string, b'123.456.789.0')

    def test_str(self):
        self.assertEqual(self.o.full_string, b"FooFamily 123.456.789.0")

        s = OSClass(family=b"AnotherFam").full_string
        self.assertEqual(s, b"AnotherFam")


class TestFullResults(unittest.TestCase):
    def setUp(self):
        u = UAClass()
        class DummyOS(object):
            @property
            def full_string(self):
                return b'Oper'
        o = DummyOS()

        self.r = FullResults(ua=u, os=o, device=b'')

    def test_full_string(self):
        self.assertEqual(self.r.full_string, b'Other/Oper')

        self.r.os = None
        self.assertEqual(self.r.full_string, b'Other')


class TestUserAgentMixin(unittest.TestCase):
    def setUp(self):
        class Foo(object):
            headers = {}

        class MixedIn(WSGIUserAgentMixin, Foo):
            pass

        self.c = MixedIn()

    def test_with_None(self):
        self.assertIsNone(self.c.user_agent)

    def test_with_value(self):
        # Value chosen semi-randomly.
        self.c.headers[b'User-Agent'] = b'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.16 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.648.133 Chrome/10.0.648.133 Safari/534.16'

        ua = self.c.user_agent
        self.assertEqual(ua.family, b'Chromium')
        self.assertEqual(ua.major, b'10')
        self.assertEqual(ua.minor, b'0')
        self.assertEqual(ua.patch, b'648')

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParsers))
    suite.addTest(unittest.makeSuite(TestOSClass))
    suite.addTest(unittest.makeSuite(TestFullResults))
    suite.addTest(unittest.makeSuite(TestUserAgentMixin))

    return suite

