# -*- coding: utf-8 -*-

from . import BaseTestCase, skip, skip_if, is_python3
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

    def test_will_escape_string(self):
        val = 'escape </> me'
        output = 'escape \\u003C/\\u003E me'
        self.assert_equal(self.app.escape_string(val), output)

    @skip
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

    def test_will_not_encapsulate_if_requested(self):
        self.app.config.json_wrap = False

        request_mock = MagicMock()
        response_mock = MagicMock()
        value = b'some val'

        self.app.on_returned_body(request_mock, response_mock, value)
        self.assert_equal(value, response_mock.body)

    def test_will_handle_non_escapable(self):
        val = '{"no_escape": 0}'
        output = '{"no_escape": 0}'
        self.assert_equal(self.app.escape_string(val), output)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHobokenJsonApplication))

    return suite

