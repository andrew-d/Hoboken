# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.accept import *


class TestAcceptList(BaseTestCase):
    def test_empty(self):
        l = AcceptList()
        self.assert_equal(len(l), 0)

    def test_parse_simple(self):
        l = AcceptList.parse('text/plain')
        self.assert_equal(l[0], ('text/plain', 1))

    def test_parse_with_quality(self):
        l = AcceptList.parse('text/plain; q=0.6')
        self.assert_equal(l[0], ('text/plain', 0.6))

    def test_parse_with_invalid_quality(self):
        l = AcceptList.parse('text/plain; q=1x')
        self.assert_true('text/plain' in l)

        q = l['text/plain']
        self.assert_equal(q, 1.0)

        l = AcceptList.parse('text/plain; q=4')
        self.assert_equal(l[0], ('text/plain', 1))

    def test_parse_with_multiple(self):
        l = AcceptList.parse('text/plain, text/html')
        self.assert_equal(l[0], ('text/plain', 1))
        self.assert_equal(l[1], ('text/html', 1))

    def test_parse_with_multiple_quality(self):
        l = AcceptList.parse('text/plain; q=0.5, text/html')
        self.assert_equal(l[0], ('text/html', 1))
        self.assert_equal(l[1], ('text/plain', 0.5))

    def test_to_string(self):
        l = AcceptList.parse('text/plain; q=0.5, text/html')
        s = str(l)

        self.assert_equal(s, 'text/html, text/plain;q=0.5')

    def test_match(self):
        l = AcceptList()
        self.assert_true(l._match('text/plain', 'text/PLAIN'))
        self.assert_true(l._match('text/plain', '*'))

    def test_accessors(self):
        l = AcceptList.parse('text/plain; q=0.5, text/html')
        self.assert_true('text/plain' in l)
        self.assert_true('text/html' in l)

        self.assert_equal(l['text/plain'], 0.5)
        self.assert_equal(l['text/html'], 1.0)


class TestMIMEAccept(BaseTestCase):
    def setup(self):
        self.m = MIMEAccept()

    def test_match_simple(self):
        self.assert_true(self.m._match(b"text/plain", b"text/plain"))
        self.assert_false(self.m._match(b"text/plain", b"text/html"))

    def test_match_invalid(self):
        with self.assert_raises(ValueError):
            self.m._match(b"foo", b"bar")

        with self.assert_raises(ValueError):
            self.m._match(b"*/invalid", b"text/plain")

    def test_match_invalid_item(self):
        self.assert_false(self.m._match(b"text/plain", b"foo"))

    def test_match_normalize(self):
        self.assert_true(self.m._match(b"TEXT/plain", b"text/PLAIN"))

    def test_match_total_wildcards(self):
        self.assert_true(self.m._match(b"*/*", b"foo/bar"))
        self.assert_true(self.m._match(b"one/two", b"*/*"))

    def test_match_partial_wildcards(self):
        self.assert_true(self.m._match(b"one/*", b"one/two"))
        self.assert_true(self.m._match(b"foo/bar", b"foo/*"))

        self.assert_false(self.m._match(b"one/*", b"two/three"))
        self.assert_false(self.m._match(b"foo/bar", b"bar/baz"))


class TestLanguageAccept(BaseTestCase):
    def setup(self):
        self.l = LanguageAccept()

    def test_simple_match(self):
        self.assert_true(self.l._match("en-US", "en-US"))

    def test_normalized_match(self):
        self.assert_true(self.l._match("en_US", "EN-us"))

    def test_wildcard_match(self):
        self.assert_true(self.l._match("en-US", "*"))


class TestCharsetAccept(BaseTestCase):
    def setup(self):
        self.c = CharsetAccept()

    def test_simple_match(self):
        self.assert_true(self.c._match("utf-8", "utf-8"))

    def test_normalize_match(self):
        self.assert_true(self.c._match("utf-8", "UTF8"))

    def test_wildcard_match(self):
        self.assert_true(self.c._match("utf-8", "*"))


class TestWSGIAcceptMixin(BaseTestCase):
    def make_obj(self, types):
        class TestObject(object):
            accept_mimetypes = []

        self.o = TestObject()
        self.o.accept_mimetypes = types

    def test_accepts_json(self):
        self.make_obj([b'application/json'])
        self.assert_true(WSGIAcceptMixin.accepts_json.__get__(self.o))

        self.make_obj([b'application/other'])
        self.assert_false(WSGIAcceptMixin.accepts_json.__get__(self.o))

    def test_accepts_xhtml(self):
        self.make_obj([b'application/xml'])
        self.assert_true(WSGIAcceptMixin.accepts_xhtml.__get__(self.o))

        self.make_obj([b'application/other'])
        self.assert_false(WSGIAcceptMixin.accepts_xhtml.__get__(self.o))

    def test_accepts_xhtml(self):
        self.make_obj([b'text/html'])
        self.o.accepts_xhtml = False
        self.assert_true(WSGIAcceptMixin.accepts_html.__get__(self.o))

        self.make_obj([b'text/plain'])
        self.o.accepts_xhtml = False
        self.assert_false(WSGIAcceptMixin.accepts_html.__get__(self.o))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAcceptList))
    suite.addTest(unittest.makeSuite(TestMIMEAccept))
    suite.addTest(unittest.makeSuite(TestLanguageAccept))
    suite.addTest(unittest.makeSuite(TestCharsetAccept))
    suite.addTest(unittest.makeSuite(TestWSGIAcceptMixin))

    return suite
