# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.request import *


class TestWSGIHeaders(BaseTestCase):
    def setup(self):
        self.environ = {
            'HTTP_HEADER': 'value',
            'HTTP_OTHER_HEADER': 'other'
        }
        self.h = WSGIHeaders(self.environ)

    def test_realname(self):
        self.assert_equal(self.h._realname('header'), 'HTTP_HEADER')
        self.assert_equal(self.h._realname('dash-header'), 'HTTP_DASH_HEADER')

        self.assert_equal(self.h._realname(b'byte-header'), b'HTTP_BYTE_HEADER')

    def test_get_item(self):
        self.assert_equal(self.h['header'], 'value')

    def test_set_item(self):
        self.h['foo'] = 'bar'
        self.assert_equal(self.h['foo'], 'bar')

        self.h['header'] = 'baz'
        self.assert_equal(self.h['header'], 'baz')

    def test_delete_item(self):
        del self.h['header']
        self.assert_true('HTTP_HEADER' not in self.environ)

    def test_misc(self):
        self.assert_equal(len(self.h), 2)

        self.assert_true('Header' in self.h)

        self.assert_equal(self.h.keys(), ['Header', 'Other-Header'])


class TestWSGIBaseRequest(BaseTestCase):
    def test_non_dict_environ(self):
        with self.assert_raises(ValueError):
            r = WSGIBaseRequest([])

    def test_headers_accessor_get(self):
        environ = {"HTTP_HEADER": "foo"}
        r = WSGIBaseRequest(environ)

        self.assert_equal(r.headers[b'Header'], b'foo')

    def test_headers_accessor_set(self):
        environ = {"HTTP_HEADER": "foo"}
        r = WSGIBaseRequest(environ)

        self.assert_equal(r.headers[b'Header'], b'foo')

        new_environ = {b'Header': b'bar', b'New-Header': b'baz'}
        r.headers = new_environ
        self.assert_equal(r.headers[b'Header'], b'bar')
        self.assert_equal(r.headers[b'New-Header'], b'baz')


class TestWSGIRequest(BaseTestCase):
    def setup(self):
        self.environ = {
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'REQUEST_METHOD': 'GET',
            'wsgi.url_scheme': 'http',
        }

        self.r = WSGIRequest(self.environ)

    def test_path_info(self):
        with patch('hoboken.objects.request.WSGIBaseRequest.path_info') as mock:
            mock.__get__ = Mock(return_value=b'foo')
            self.assert_equal(self.r.path_info, b'/foo')

            mock.__get__ = Mock(return_value=b'/foo')
            self.assert_equal(self.r.path_info, b'/foo')

    def test_host_with_port(self):
        self.r.headers[b'Host'] = 'foo:81'
        self.assert_equal(self.r.host_with_port, 'foo:81')
        del self.r.headers[b'Host']

    def test_host_with_port_no_header(self):
        self.assert_equal(self.r.host_with_port, 'localhost')
        self.environ['SERVER_PORT'] = '81'
        self.assert_equal(self.r.host_with_port, 'localhost:81')

    def test_host_with_port_no_header_https(self):
        self.environ['wsgi.url_scheme'] = 'https'
        self.environ['SERVER_PORT'] = '443'

        self.assert_equal(self.r.host_with_port, 'localhost')
        self.environ['SERVER_PORT'] = '444'
        self.assert_equal(self.r.host_with_port, 'localhost:444')

    def test_host(self):
        self.assert_equal(self.r.host, 'localhost')

        self.environ['SERVER_PORT'] = '444'
        self.assert_equal(self.r.host, 'localhost')

    def test_port(self):
        self.environ['SERVER_PORT'] = '444'
        self.assert_equal(self.r.port, 444)

    def test_port_with_forwarding(self):
        self.r.headers[b'X-Forwarded-Port'] = '1234'
        self.assert_equal(self.r.port, 1234)

    # def test_port_by_scheme(self):
    #     self.environ['wsgi.url_scheme'] = b'https'
    #     self.assert_equal(self.r.port, 443)

    def test_path(self):
        class TestClass(object):
            script_name = b'script/'
            path_info = b'path_info'

        c = TestClass()

        self.assert_equal(WSGIRequest.path.__get__(c), 'script/path_info')

    def test_full_path(self):
        class TestClass(object):
            path = b'script/path_info'
            query_string = b''

        c = TestClass()

        self.assert_equal(WSGIRequest.full_path.__get__(c), 'script/path_info')

        c.query_string = b'foo=bar'
        self.assert_equal(WSGIRequest.full_path.__get__(c), 'script/path_info?foo=bar')

    def test_url(self):
        class TestClass(object):
            scheme = b'http'
            host_with_port = b'localhost:1234'
            path = b'script/path_info'
            query_string = b''

        c = TestClass()

        self.assert_equal(WSGIRequest.url.__get__(c), 'http://localhost:1234/script/path_info')

        c.query_string = b'foo=bar'
        self.assert_equal(WSGIRequest.url.__get__(c), 'http://localhost:1234/script/path_info?foo=bar')

    def test_is_secure(self):
        class TestClass(object):
            scheme = 'http'

        c = TestClass()
        self.assert_false(WSGIRequest.is_secure.__get__(c))

        c.scheme = 'https'
        self.assert_true(WSGIRequest.is_secure.__get__(c))




def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIHeaders))
    suite.addTest(unittest.makeSuite(TestWSGIBaseRequest))
    suite.addTest(unittest.makeSuite(TestWSGIRequest))

    return suite

