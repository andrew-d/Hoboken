# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.authorization import *


class TestAuthorization(BaseTestCase):
    def test_basic_auth(self):
        o = Authorization.parse(b'Basic dXNlcm5hbWU6cGFzc3dvcmQ=')
        self.assert_equal(o.type, b'Basic')
        self.assert_equal(o.params[b'username'], b'username')
        self.assert_equal(o.params[b'password'], b'password')

    def test_basic_no_split(self):
        o = Authorization.parse(b'Basic Zm9vYmFy')
        self.assert_equal(o.type, b'Basic')
        self.assert_equal(o.params, b'Zm9vYmFy')

    def test_with_params(self):
        o = Authorization.parse(b'Basic realm="ARealm"')
        self.assert_equal(o.type, b'Basic')
        self.assert_equal(o.params[b'realm'], b'ARealm')

    def test_invalid_parse(self):
        o = Authorization.parse(None)
        self.assert_true(o is None)

        o = Authorization.parse(b'Basic invalid')
        self.assert_equal(o.params, b'invalid')

    def test_serialize_basic(self):
        o = Authorization(b'Basic', {b'username': b'username', b'password': b'password'})
        s = o.serialize()
        self.assert_equal(s, b'Basic dXNlcm5hbWU6cGFzc3dvcmQ=')

    def test_serialize_params(self):
        o = Authorization(b'Basic', {b'realm': b'ARealm'})
        s = o.serialize()
        self.assert_equal(s, b'Basic realm="ARealm"')


class TestMixins(BaseTestCase):
    def test_request(self):
        w = WSGIRequestAuthorizationMixin()
        w.headers = {}
        w.headers['Authorization'] = b'Basic qqqq'
        self.assert_true(isinstance(w.authorization, Authorization))

    def test_response(self):
        w = WSGIResponseAuthorizationMixin()
        w.headers = {}
        w.headers['WWW-Authenticate'] = b'Basic realm="foo"'
        self.assert_true(isinstance(w.www_authenticate, Authorization))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAuthorization))
    suite.addTest(unittest.makeSuite(TestMixins))

    return suite

