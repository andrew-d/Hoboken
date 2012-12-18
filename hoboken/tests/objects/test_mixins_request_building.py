# -*- coding: utf-8 -*-

from . import BaseTestCase
import sys
import unittest
from mock import MagicMock, call, patch

from hoboken.objects.mixins.request_building import *


class TestBuildMethod(BaseTestCase):
    DEFAULT_ENV = {
        'SERVER_PROTOCOL': 'HTTP/1.0',
        'SCRIPT_NAME': '',
        'PATH_INFO': '/',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'http',
        'wsgi.multithread': False,
        'wsgi.multiprocess': False,
        'wsgi.run_once': False,
        'REQUEST_METHOD': 'GET',
        'SERVER_NAME': 'localhost',
        'SERVER_PORT': '80',
    }

    def setup(self):
        self.req = MagicMock()
        self.req_type = MagicMock()
        self.req_type.return_value = self.req

    def build(self, *args, **kwargs):
        WSGIRequestBuilderMixin.build.__func__(self.req_type, *args, **kwargs)

    def assert_env(self, path, **kwargs):
        env = self.DEFAULT_ENV.copy()
        env.update(kwargs)
        env['PATH_INFO'] = path

        self.req_type.assert_called_with(env)

    def assert_headers(self, *header_list):
        for x in header_list:
            c = call(*x)
            self.assert_true(c in self.req.headers.__setitem__.call_args_list)

    def test_default(self):
        self.build('/')
        self.req_type.assert_called_with(self.DEFAULT_ENV)

    def test_given_path(self):
        self.build('/foo')
        self.assert_env('/foo')

    def test_headers(self):
        self.build('/', headers={'Content-Type': b'text/plain'})
        self.assert_headers(('Content-Type', b'text/plain'))

    def test_multiple_headers(self):
        self.build('/', headers={'Content-Type': b'text/plain', 'X-Foo': b'bar'})
        self.assert_headers(('Content-Type', b'text/plain'), ('X-Foo', b'bar'))

    def test_set_method(self):
        self.build('/', method='POST')
        self.assert_env('/', REQUEST_METHOD='POST')

    def test_set_server_name(self):
        self.build('/', server_name='www.foobar.com')
        self.assert_env('/', SERVER_NAME='www.foobar.com')

    def test_set_server_port(self):
        self.build('/', server_port='1234')
        self.assert_env('/', SERVER_PORT='1234')

    def test_set_query_string(self):
        self.build('/', query_string='foo=bar&asdf=baz')
        self.assert_env('/', QUERY_STRING='foo=bar&asdf=baz')


class TestCallApplication(BaseTestCase):
    def setup(self):
        # Default values to return.
        self.return_val = None
        self.return_iter = None
        self.return_headers = None

        def dummy_app(environ, start_response):
            # Save environ.
            self.environ = environ

            # Call start_response.
            start_response(self.return_val, self.return_headers)
            return self.return_iter

        self.app = dummy_app

        class DummyObject(object):
            def __init__(self, environ):
                self.environ = environ

            headers = {}

        class MixedIn(WSGIRequestBuilderMixin, DummyObject):
            pass

        self.Type = MixedIn

    def build_and_call(self, path, status='200 OK', headers=[],
                       iter=[], **kwargs):
        self.req = self.Type.build(path, **kwargs)
        self.return_val = status
        self.return_headers = headers
        self.return_iter = iter

        return self.req.call_application(self.app)

    def test_simple_call(self):
        status, headers, it = self.build_and_call('/')
        self.assert_equal(self.environ, self.req.environ)
        self.assert_equal(status, self.return_val)
        self.assert_equal(headers, self.return_headers)
        self.assert_equal(it, self.return_iter)

    def test_call_with_status(self):
        status, headers, it = self.build_and_call('/', status='403 Forbidden')

        self.assert_equal(status, '403 Forbidden')

    def test_call_with_iter(self):
        exp = [b'foo', b'bar']
        status, headers, it = self.build_and_call('/', iter=exp)
        self.assert_equal(it, exp)

    def test_call_will_close(self):
        it = MagicMock()
        status, headers, it = self.build_and_call('/', iter=it)

        it.close.assert_called()

    def test_call_write_function(self):
        app_it = MagicMock()

        def dummy_app(environ, start_response):
            # Call start_response.
            writer = start_response(self.return_val, self.return_headers)
            writer(b'foo')
            writer(b'bar')
            return app_it

        self.req = self.Type.build('/')
        status, headers, it = self.req.call_application(dummy_app)

        self.assert_equal(list(it), [b'foo', b'bar'])
        app_it.close.assert_called_once_with()

    def test_call_application_with_exception(self):
        def dummy_app(environ, start_response):
            try:
                1 / 0
                start_response("200 OK", [])
                return [b'normal']
            except Exception:
                start_response("500 Internal Server Error", [], sys.exc_info())
                return [b'error']

        self.req = self.Type.build('/')

        with self.assert_raises(ZeroDivisionError):
            status, headers, it = self.req.call_application(dummy_app)

        status, headers, it, err = self.req.call_application(dummy_app, catch_exc_info=True)

    def test_get_response(self):
        self.req = self.Type.build('/')
        self.return_val = '200 OK'
        self.return_headers = []
        self.return_iter = []
        self.req.ResponseClass = MagicMock
        resp = self.req.get_response(self.app)

        self.assert_true(isinstance(resp, MagicMock))
        self.assert_equal(resp.status, self.return_val)
        self.assert_equal(resp.headers, self.return_headers)
        self.assert_equal(resp.response_iter, self.return_iter)

    def test_get_response_with_err(self):
        def dummy_app(environ, start_response):
            try:
                1 / 0
                start_response("200 OK", [])
                return [b'normal']
            except Exception:
                start_response("500 Internal Server Error", [], sys.exc_info())
                return [b'error']

        self.req = self.Type.build('/')
        self.req.ResponseClass = MagicMock
        resp = self.req.get_response(dummy_app, catch_exc_info=True)
        self.assert_equal(resp.status, '500 Internal Server Error')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBuildMethod))
    suite.addTest(unittest.makeSuite(TestCallApplication))

    return suite

