# -*- coding: utf-8 -*-

from . import BaseTestCase, skip, parametrize, parameters
import os
import sys
import yaml
import unittest

from hoboken.objects.mixins.user_agent import *


class TestParsers(BaseTestCase):
    def setup(self):
        self.d = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "ua_tests"
        )

    def assert_ua_results(self, results, expected):
        self.assert_equal(results.ua.family, expected['family'])
        self.assert_equal(results.ua.major, expected['major'])
        self.assert_equal(results.ua.minor, expected['minor'])
        self.assert_equal(results.ua.patch, expected['patch'])

    def assert_os_results(self, results, expected):
        self.assert_equal(results.os.family, expected['family'])
        self.assert_equal(results.os.major, expected['major'])
        self.assert_equal(results.os.minor, expected['minor'])
        self.assert_equal(results.os.patch, expected['patch'])

    def assert_device_results(self, results, expected):
        self.assert_equal(results.device, expected['family'])

    def check_from_file(self, file, assert_func):
        with open(os.path.join(self.d, file), 'rb') as f:
            contents = yaml.load(f)

        for test_case in contents['test_cases']:
            ua_string = test_case['user_agent_string']

            # We skip JS tests, since our library is server-side only for now.
            if 'js_ua' in test_case:
                continue

            r = parser.parse_all(ua_string)
            assert_func(r, test_case)
            # self.assert_ua_results(r, test_case)

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
            family="FooFamily",
            major='123',
            minor='456',
            patch='789',
            patch_minor='0'
        )

    def test_version_string(self):
        self.assert_equal(self.o.version_string, '123.456.789.0')

    def test_str(self):
        s = str(self.o)
        self.assert_equal(s, "FooFamily 123.456.789.0")

        s = str(OSClass(family="AnotherFam"))
        self.assert_equal(s, "AnotherFam")


class TestFullResults(BaseTestCase):
    def setup(self):
        u = UAClass()
        self.r = FullResults(ua=u, os='Oper', device='')

    def test_full_string(self):
        self.assert_equal(self.r.full_string, 'Other/Oper')

        self.r.os = None
        self.assert_equal(self.r.full_string, 'Other')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParsers))
    suite.addTest(unittest.makeSuite(TestOSClass))
    suite.addTest(unittest.makeSuite(TestFullResults))

    return suite

