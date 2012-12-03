# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.date import *


class TestDateHeader(BaseTestCase):
    def setup(self):
        class C(object):
            _parse_date = MagicMock()
            _serialize_date = MagicMock()
            headers = {}
            p = date_header_property('Date')
            rp = date_header_property('Date2', read_only=True)

        self.c = C()

        self.get_mock = self.c._parse_date
        self.get_mock.side_effect = lambda x: x

        self.set_mock = self.c._serialize_date
        self.set_mock.side_effect = lambda x: x

    def test_getter(self):
        self.c.headers['Date'] = b'foo'
        self.assert_equal(self.c.p, b'foo')
        self.get_mock.assert_called_once_with(b'foo')

    def test_setter(self):
        self.c.p = b'foo'
        self.assert_equal(self.c.headers['Date'], b'foo')
        self.set_mock.assert_called_once_with(b'foo')

        self.c.p = None
        self.assert_true('Date' not in self.c.headers)

    def test_readonly_fails(self):
        with self.assert_raises(AttributeError):
            self.c.rp = b'bad'


class TestWSGIResponseDateMixin(BaseTestCase):
    def setup(self):
        self.d = WSGIResponseDateMixin()
        self.d.headers = {}


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIResponseDateMixin))
    suite.addTest(unittest.makeSuite(TestDateHeader))

    return suite
