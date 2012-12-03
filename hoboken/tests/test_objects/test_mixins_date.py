# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.date import *
import datetime      # After above, since it clobbers datetime


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

    def test_deleter(self):
        self.c.headers['Date'] = b'foobar'
        del self.c.p

        self.assert_true('Date' not in self.c.headers)


class TestWSGIDateMixin(BaseTestCase):
    def setup(self):
        self.d = WSGIDateMixin()
        self.d.headers = {}

        base_time = datetime.datetime(2012, 12, 3, 0, 0, 0)
        self.d._WSGIDateMixin__now = lambda: base_time

    def test_basic(self):
        self.d.date = b'123'
        self.assert_equal(self.d.headers['Date'], b'123')

        self.d.date = b'123'.decode('latin-1')
        self.assert_equal(self.d.headers['Date'], b'123')

    def test_with_timedelta(self):
        self.d.date = timedelta(seconds=10)
        self.assert_equal(self.d.date, datetime.datetime(2012, 12, 3, 0, 0, 10))

    def test_with_date(self):
        self.d.date = datetime.date(2012, 12, 3)
        self.assert_equal(self.d.date, datetime.datetime(2012, 12, 3, 0, 0, 0))

    def test_with_invalid(self):
        with self.assert_raises(ValueError):
            self.d.date = []

    def test_invalid_parse(self):
        self.assert_true(self.d._parse_date(b'bad-date') is None)

    def test_without_timezone(self):
        v = 'Mon, 03 Dec 2012 00:00:00'
        parsed = self.d._parse_date(v)
        serialized = self.d._serialize_date(parsed)
        self.assert_equal(serialized, 'Mon, 03 Dec 2012 00:00:00 GMT')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestDateHeader))
    suite.addTest(unittest.makeSuite(TestWSGIDateMixin))

    return suite
