# -*- coding: utf-8 -*-

from hoboken.tests.compat import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.authorization import *


class TestAuthorization(unittest.TestCase):
    def assert_parse(self, input, type, params):
        parsed_type, parsed_params = parse_auth(input)
        self.assertEqual(parsed_type, type)
        self.assertEqual(parsed_params, params)

    def assert_serialize(self, type, params, output):
        ser = serialize_auth((type, params))
        self.assertEqual(ser, output)

    def test_basic_auth(self):
        self.assert_parse(b'Basic Zm9vYmFy', b'Basic', b'Zm9vYmFy')

    def test_with_params(self):
        self.assert_parse(b'Basic realm="ARealm"', b'Basic', {b'realm': b'ARealm'})

    def test_invalid_parse(self):
        o = parse_auth(None)
        self.assertIsNone(o)

    def test_serialize_basic(self):
        self.assert_serialize(
            b'Basic',
            b'Foobar',
            b'Basic Foobar'
        )

    def test_serialize_params(self):
        self.assert_serialize(
            b'Basic',
            {b'realm': b'ARealm'},
            b'Basic realm="ARealm"'
        )

    def test_serialize_bad(self):
        self.assertEqual(serialize_auth(123), 123)

        with self.assertRaises(ValueError):
            serialize_auth([123, 123])


class TestMixins(unittest.TestCase):
    def test_request(self):
        w = WSGIRequestAuthorizationMixin()
        w.headers = {}
        w.headers[b'Authorization'] = b'Basic qqqq'
        type, params = w.authorization
        self.assertEqual(type, b'Basic')
        self.assertEqual(params, b'qqqq')

        w.authorization = (b'Basic', b'Foobar')
        self.assertEqual(w.headers[b'Authorization'], b'Basic Foobar')

    def test_response(self):
        w = WSGIResponseAuthorizationMixin()
        w.headers = {}
        w.headers[b'WWW-Authenticate'] = b'Basic realm="foo"'
        type, params = w.www_authenticate
        self.assertEqual(type, b'Basic')
        self.assertEqual(params, {b'realm': b'foo'})

        w.www_authenticate = (b'Basic', b'Foobar')
        self.assertEqual(w.headers[b'WWW-Authenticate'], b'Basic Foobar')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAuthorization))
    suite.addTest(unittest.makeSuite(TestMixins))

    return suite

