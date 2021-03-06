# -*- coding: utf-8 -*-

from hoboken.tests.compat import unittest
from mock import MagicMock, Mock, patch

from hoboken.six import u
from hoboken.objects.request import *


class TestWSGIBaseRequest(unittest.TestCase):
    def setUp(self):
        # Note that we can't directly instantiate a WSGIBaseRequest, since
        # it's still abstract.
        class ImplClass(WSGIBaseRequest):
            host = None
            path = None
            port = None
            url = None

        self.C = ImplClass

    def test_non_dict_environ(self):
        with self.assertRaises(ValueError):
            r = self.C([])

    def test_headers_accessor_get(self):
        environ = {"HTTP_HEADER": "foo"}
        r = self.C(environ)

        self.assertEqual(r.headers[b'Header'], b'foo')

    def test_headers_accessor_set(self):
        environ = {"HTTP_HEADER": "foo"}
        r = self.C(environ)

        self.assertEqual(r.headers[b'Header'], b'foo')

        new_environ = {b'Header': b'bar', b'New-Header': b'baz'}
        r.headers = new_environ
        self.assertEqual(r.headers[b'Header'], b'bar')
        self.assertEqual(r.headers[b'New-Header'], b'baz')


class TestWSGIRequest(unittest.TestCase):
    def setUp(self):
        self.environ = {
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'REQUEST_METHOD': 'GET',
            'wsgi.url_scheme': 'http',
        }

        self.r = WSGIRequest(self.environ)

    def test_method(self):
        self.assertEqual(self.r.method, 'GET')

        self.r.method = u('POST')
        self.assertEqual(self.r.method, 'POST')

        self.r.method = b'PUT'
        self.assertEqual(self.r.method, 'PUT')

    def test_path_info(self):
        with patch('hoboken.objects.request.WSGIBaseRequest.path_info') as m:
            m.__get__ = Mock(return_value=b'foo')
            self.assertEqual(self.r.path_info, b'/foo')

            m.__get__ = Mock(return_value=b'/foo')
            self.assertEqual(self.r.path_info, b'/foo')

    def test_host_with_port(self):
        self.r.headers[b'Host'] = 'foo:81'
        self.assertEqual(self.r.host_with_port, b'foo:81')
        del self.r.headers[b'Host']

    def test_host_with_port_no_header(self):
        self.assertEqual(self.r.host_with_port, b'localhost')
        self.environ['SERVER_PORT'] = '81'
        self.assertEqual(self.r.host_with_port, b'localhost:81')

    def test_host_with_port_no_header_https(self):
        self.environ['wsgi.url_scheme'] = 'https'
        self.environ['SERVER_PORT'] = '443'

        self.assertEqual(self.r.host_with_port, b'localhost')
        self.environ['SERVER_PORT'] = '444'
        self.assertEqual(self.r.host_with_port, b'localhost:444')

    def test_host(self):
        self.assertEqual(self.r.host, b'localhost')

        self.environ['SERVER_PORT'] = '444'
        self.assertEqual(self.r.host, b'localhost')

    def test_port(self):
        self.environ['SERVER_PORT'] = '444'
        self.assertEqual(self.r.port, 444)

    def test_port_with_forwarding(self):
        self.r.headers[b'X-Forwarded-Port'] = '1234'
        self.assertEqual(self.r.port, 1234)

    def test_port_with_host_forwarding(self):
        self.r.headers[b'X-Forwarded-Host'] = 'foobar'
        self.assertEqual(self.r.port, 80)

    def test_port_with_server_port(self):
        self.r.headers[b'Host'] = b'localhost'
        self.environ['SERVER_PORT'] = '444'
        self.assertEqual(self.r.port, 444)

    def test_port_by_scheme(self):
        # XXX: I'm not convinced this is correct.
        self.environ['wsgi.url_scheme'] = 'https'
        self.environ['SERVER_PORT'] = '443'
        self.assertEqual(self.r.port, 443)

    def test_path(self):
        class TestClass(object):
            script_name = b'script/'
            path_info = b'path_info'

        c = TestClass()

        self.assertEqual(WSGIRequest.path.__get__(c), b'script/path_info')

    def test_full_path(self):
        class TestClass(object):
            path = b'script/path_info'
            query_string = b''

        c = TestClass()

        self.assertEqual(WSGIRequest.full_path.__get__(c),
                         b'script/path_info')

        c.query_string = b'foo=bar'
        self.assertEqual(WSGIRequest.full_path.__get__(c),
                         b'script/path_info?foo=bar')

    def test_url(self):
        class TestClass(object):
            scheme = b'http'
            host_with_port = b'localhost:1234'
            path = b'script/path_info'
            query_string = b''

        c = TestClass()

        self.assertEqual(WSGIRequest.url.__get__(c),
                         b'http://localhost:1234/script/path_info')

        c.query_string = b'foo=bar'
        self.assertEqual(WSGIRequest.url.__get__(c),
                         b'http://localhost:1234/script/path_info?foo=bar')

    def test_is_secure(self):
        class TestClass(object):
            scheme = b'http'

        c = TestClass()
        self.assertFalse(WSGIRequest.is_secure.__get__(c))

        c.scheme = b'https'
        self.assertTrue(WSGIRequest.is_secure.__get__(c))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIBaseRequest))
    suite.addTest(unittest.makeSuite(TestWSGIRequest))

    return suite

