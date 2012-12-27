# -*- coding: utf-8 -*-

from hoboken.ext.json_app import HobokenJsonApplication

from hoboken.tests.compat import unittest
from mock import patch, MagicMock

from hoboken.six import u

class TestHobokenJsonApplication(unittest.TestCase):
    def setUp(self):
        self.app = HobokenJsonApplication('')

    def test_will_set_default_indent_config(self):
        self.assertIn('json_indent', self.app.config)

    def test_will_set_default_escape_config(self):
        self.assertEqual(self.app.config['JSON_ESCAPE'], True)

    def test_will_escape_string(self):
        val = b'escape </> me'.decode('latin-1')
        output = b'escape \\u003C/\\u003E me'.decode('latin-1')
        self.assertEqual(self.app.escape_string(val), output)

    def test_will_escape_bytes(self):
        val = b'escape </> me'
        output = b'escape \\u003C/\\u003E me'
        self.assertEqual(self.app.escape_string(val), output)

    def test_will_not_escape_if_requested(self):
        self.app.config['JSON_ESCAPE'] = False
        request_mock = MagicMock()
        response_mock = MagicMock()
        val = {'foo': 'dont escape </> me'}

        with patch('json.dumps', return_value='') as json_mock:
            self.app.on_returned_body(request_mock, response_mock, val)

        json_mock.assert_called_with(val, indent=self.app.config['JSON_INDENT'])

    def test_will_encapsulate_value(self):
        request_mock = MagicMock()
        response_mock = MagicMock()
        value = 'foobar'

        with patch('json.dumps', return_value='') as json_mock:
            self.app.on_returned_body(request_mock, response_mock, value)

        json_mock.assert_called_with({'value': value}, indent=self.app.config['JSON_INDENT'])

    def test_will_not_encapsulate_if_requested(self):
        self.app.config['JSON_WRAP'] = False

        request_mock = MagicMock()
        response_mock = MagicMock()
        value = b'some val'

        self.app.on_returned_body(request_mock, response_mock, value)
        self.assertEqual(value, response_mock.body)

    def test_will_handle_non_escapable(self):
        val = '{"no_escape": 0}'
        output = '{"no_escape": 0}'
        self.assertEqual(self.app.escape_string(val), output)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestHobokenJsonApplication))

    return suite

