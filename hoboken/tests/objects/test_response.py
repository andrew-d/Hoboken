# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.response import *


class TestWSGIBaseResponse(unittest.TestCase):
    def setUp(self):
        self.e = WSGIBaseResponse()

    def test_status_defaults_to_success(self):
        self.assertEqual(self.e.status_int, 200)

    def test_status_int(self):
        self.e.status_int = 300
        self.assertEqual(self.e.status_int, 300)

    def test_status_int_fails(self):
        with self.assertRaises(ValueError):
            self.e.status_int = 600

    def test_status_text(self):
        self.e.status_int = 200
        self.assertEqual(self.e.status_text, 'OK')

    def test_status_text_other_code(self):
        self.e.status_int = 299
        self.assertEqual(self.e.status_text, 'Success')

        self.e.status_int = 599
        self.assertEqual(self.e.status_text, 'Unknown Server Error')

    def test_status(self):
        self.e.status_int = 200
        self.assertEqual(self.e.status, '200 OK')

    def test_status_setter(self):
        self.e.status = '301 Moved Permanently'
        self.assertEqual(self.e.status_int, 301)

    def test_headers(self):
        self.e.headers['Cache-Control'] = b'foo'
        self.assertEqual(self.e.headers['Cache-Control'], b'foo')

    def test_response_iter(self):
        self.e.response_iter = [b'a', b'b', b'c']
        self.assertEqual(list(self.e.response_iter), [b'a', b'b', b'c'])

    def test_response_iter_fails(self):
        with self.assertRaises(ValueError):
            self.e.response_iter = 123

    def test_will_close_iter(self):
        class TestIter(object):
            def __iter__(self):
                return self

            def close(self):
                self.closed = True

            def next(self):
                return StopIteration()

            __next__ = next

        i = TestIter()
        self.e.response_iter = i
        self.e.close()
        self.assertTrue(i.closed)

    def test___call__(self):
        start_response = MagicMock()
        environ = {"REQUEST_METHOD": "GET"}
        self.e.headers['Response-Header'] = b'value'

        it = self.e(environ, start_response)

        self.assertEqual(it, [b''])
        start_response.assert_called_with("200 OK",
            [('Response-Header', b'value')]
        )


class TestEmptyResponse(unittest.TestCase):
    def setUp(self):
        self.r = EmptyResponse()

    def test_is_empty(self):
        self.assertEqual(len(self.r), 0)
        self.assertEqual(list(self.r), [])

    def test_will_call_close(self):
        m = MagicMock()
        r = EmptyResponse(response_iter=m)
        r.close()

        m.close.assert_called_once()


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIBaseResponse))
    suite.addTest(unittest.makeSuite(TestEmptyResponse))

    return suite

