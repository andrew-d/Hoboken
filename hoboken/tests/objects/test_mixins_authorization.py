# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.authorization import *


class TestAuthorization(BaseTestCase):
    def assert_parse(self, input, type, params):
        parsed_type, parsed_params = parse_auth(input)
        self.assert_equal(parsed_type, type)
        self.assert_equal(parsed_params, params)

    def assert_serialize(self, type, params, output):
        ser = serialize_auth((type, params))
        self.assert_equal(ser, output)

    def test_basic_auth(self):
        self.assert_parse(b'Basic Zm9vYmFy', b'Basic', b'Zm9vYmFy')

    def test_with_params(self):
        self.assert_parse(b'Basic realm="ARealm"', b'Basic', {b'realm': b'ARealm'})

    def test_invalid_parse(self):
        o = parse_auth(None)
        self.assert_true(o is None)

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


class TestMixins(BaseTestCase):
    def test_request(self):
        w = WSGIRequestAuthorizationMixin()
        w.headers = {}
        w.headers[b'Authorization'] = b'Basic qqqq'
        type, params = w.authorization
        self.assert_equal(type, b'Basic')
        self.assert_equal(params, b'qqqq')

    def test_response(self):
        w = WSGIResponseAuthorizationMixin()
        w.headers = {}
        w.headers[b'WWW-Authenticate'] = b'Basic realm="foo"'
        type, params = w.www_authenticate
        self.assert_equal(type, b'Basic')
        self.assert_equal(params, {b'realm': b'foo'})


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAuthorization))
    suite.addTest(unittest.makeSuite(TestMixins))

    return suite

