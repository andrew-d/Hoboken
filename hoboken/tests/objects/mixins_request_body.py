# -*- coding: utf-8 -*-

from . import BaseTestCase, skip
import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.request_body import *


class TestParseContentType(BaseTestCase):
    def test_simple(self):
        t, p = parse_content_type(b'application/json')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {})

    def test_single_param(self):
        t, p = parse_content_type(b'application/json;par=val')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'par': b'val'})

    def test_multiple_params(self):
        t, p = parse_content_type(b'application/json;par=val;asdf=foo')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'par': b'val', b'asdf': b'foo'})

    @skip('FIXME: Currently failing')
    def test_quoted_param(self):
        t, p = parse_content_type(b'application/json;param="quoted"')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'param': b'quoted'})

    @skip('FIXME: Currently failing')
    def test_quoted_param_with_semicolon(self):
        t, p = parse_content_type(b'application/json;param="quoted;with;semicolons"')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'param': b'quoted;with;semicolons'})


class TestQuerystringParser(BaseTestCase):
    def on_field(self, val):
        self.f.append(val)

    def assert_fields(self, *args, **kwargs):
        self.assert_equal(self.f, list(args))
        if kwargs.get('reset', True):
            self.f = []

    def setup(self):
        self.f = []
        self.p = QuerystringParser(self.on_field)

    def test_simple_querystring(self):
        self.p.write(b'foo=bar')
        self.p.write(b'')

        self.assert_fields(Field(name=b'foo', value=b'bar'))

    def test_multiple_querystring(self):
        self.p.write(b'foo=bar&asdf=baz')
        self.p.write(b'')

        self.assert_fields(
            Field(name=b'foo', value=b'bar'),
            Field(name=b'asdf', value=b'baz')
        )

    def test_streaming_simple(self):
        self.p.write(b'foo=bar&')
        self.assert_fields(
            Field(name=b'foo', value=b'bar'),
        )

        self.p.write(b'asdf=baz')
        self.p.write(b'')
        self.assert_fields(
            Field(name=b'asdf', value=b'baz')
        )

    def test_streaming_break(self):
        self.p.write(b'foo=one')
        self.assert_fields()

        self.p.write(b'two')
        self.assert_fields()

        self.p.write(b'three')
        self.assert_fields()

        self.p.write(b'&asd')
        self.assert_fields(
            Field(name=b'foo', value=b'onetwothree')
        )

        self.p.write(b'f=baz')
        self.p.write(b'')
        self.assert_fields(
            Field(name=b'asdf', value=b'baz')
        )

    def test_semicolon_seperator(self):
        self.p.write(b'foo=bar;asdf=baz')
        self.p.write(b'')

        self.assert_fields(
            Field(name=b'foo', value=b'bar'),
            Field(name=b'asdf', value=b'baz')
        )

    # TODO: test overlarge fields, blank values, and strict parsing



class TestRequestBodyMixin(BaseTestCase):
    def setup(self):
        pass



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParseContentType))
    suite.addTest(unittest.makeSuite(TestQuerystringParser))
    suite.addTest(unittest.makeSuite(TestRequestBodyMixin))

    return suite

