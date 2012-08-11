# -*- coding: utf-8 -*-

from . import BaseTestCase, skip_if, is_python3
from ..ext import HobokenJsonApplication
import unittest
from mock import patch, MagicMock
from webob import Request

class TestHobokenJsonApplication(BaseTestCase):
    def setup(self):
        self.app = HobokenJsonApplication('')

    def test_will_set_default_indent_config(self):
        self.assert_true('json_indent' in self.app.config)

    def test_will_set_default_escape_config(self):
        self.assert_equal(self.app.config.json_escape, True)

    def test_will_escape_dict(self):
        val = {'foo': 'esc<ape me'}
        output = {'foo': 'esc\\u003Cape me'}
        self.assert_equal(self.app.recursive_escape(val), output)

    def test_will_escape_list(self):
        val = ['foo', 'b<ar']
        output = ['foo', 'b\\u003Car']
        self.assert_equal(self.app.recursive_escape(val), output)

    def test_will_escape_tuple(self):
        val = ('foo', 'b<ar')
        output = ('foo', 'b\\u003Car')
        self.assert_equal(self.app.recursive_escape(val), output)

    def test_will_escape_string(self):
        val = 'escape </> me'
        output = 'escape \\u003C\\u002F\\u003E me'
        self.assert_equal(self.app.recursive_escape(val), output)

    def test_will_escape_bytes(self):
        val = b'escape </> me'
        output = b'escape \\u003C\\u002F\\u003E me'
        self.assert_equal(self.app.recursive_escape(val), output)

    def test_will_not_escape_if_requested(self):
        self.app.config.json_escape = False
        request_mock = MagicMock()
        response_mock = MagicMock()
        val = {'foo': 'dont escape </> me'}

        with patch('json.dumps', return_value='') as json_mock:
            self.app.on_returned_body(request_mock, response_mock, val)

        json_mock.assert_called_with(val, indent=self.app.config.json_indent)

    def test_will_encapsulate_value(self):
        request_mock = MagicMock()
        response_mock = MagicMock()
        value = 'foobar'

        with patch('json.dumps', return_value='') as json_mock:
            self.app.on_returned_body(request_mock, response_mock, value)

        json_mock.assert_called_with({'value': value}, indent=self.app.config.json_indent)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHobokenJsonApplication))

    return suite
