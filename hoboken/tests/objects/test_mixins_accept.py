# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.accept import *


class TestAcceptList(unittest.TestCase):
    def test_empty(self):
        l = AcceptList()
        self.assertEqual(len(l), 0)

    def test_parse_simple(self):
        l = AcceptList.parse(b'text/plain')
        self.assertEqual(l[0], (b'text/plain', 1))

    def test_parse_with_quality(self):
        l = AcceptList.parse(b'text/plain; q=0.6')
        self.assertEqual(l[0], (b'text/plain', 0.6))

    def test_parse_with_invalid_quality(self):
        l = AcceptList.parse(b'text/plain; q=1x')
        self.assertIn(b'text/plain', l)

        # q = l[b'text/plain']
        # self.assertEqual(q, 1.0)

        l = AcceptList.parse(b'text/plain; q=4')
        self.assertEqual(l[0], (b'text/plain', 1))

    def test_parse_with_multiple(self):
        l = AcceptList.parse(b'text/plain, text/html')
        self.assertEqual(l[0], (b'text/plain', 1))
        self.assertEqual(l[1], (b'text/html', 1))

    def test_parse_with_multiple_quality(self):
        l = AcceptList.parse(b'text/plain; q=0.5, text/html')
        self.assertEqual(l[0], (b'text/html', 1))
        self.assertEqual(l[1], (b'text/plain', 0.5))

    def test_to_bytes(self):
        l = AcceptList.parse(b'text/plain; q=0.5, text/html')
        s = l.to_bytes()

        self.assertEqual(s, b'text/html, text/plain;q=0.5')

    def test_match(self):
        l = AcceptList()
        self.assertTrue(l._match(b'text/plain', b'text/PLAIN'))
        self.assertTrue(l._match(b'text/plain', b'*'))

    def test_accessors(self):
        l = AcceptList.parse(b'text/plain; q=0.5, text/html')
        self.assertIn(b'text/plain', l)
        self.assertIn(b'text/html', l)

        self.assertEqual(l[b'text/plain'], 0.5)
        self.assertEqual(l[b'text/html'], 1.0)

        v = b'text/plain'.decode('latin-1')
        self.assertEqual(l[v], 0.5)

    def test_quality_fails(self):
        l = AcceptList.parse(b'text/plain')
        self.assertEqual(l[b'text/html'], 0)

    def test_invalid_parse(self):
        l = AcceptList.parse(None)
        self.assertTrue(l is None)


class TestMIMEAccept(unittest.TestCase):
    def setUp(self):
        self.m = MIMEAccept()

    def test_match_simple(self):
        self.assertTrue(self.m._match(b"text/plain", b"text/plain"))
        self.assertFalse(self.m._match(b"text/plain", b"text/html"))

    def test_match_invalid(self):
        with self.assertRaises(ValueError):
            self.m._match(b"foo", b"bar")

        with self.assertRaises(ValueError):
            self.m._match(b"*/invalid", b"text/plain")

    def test_match_invalid_item(self):
        self.assertFalse(self.m._match(b"text/plain", b"foo"))

    def test_match_normalize(self):
        self.assertTrue(self.m._match(b"TEXT/plain", b"text/PLAIN"))

    def test_match_total_wildcards(self):
        self.assertTrue(self.m._match(b"*/*", b"foo/bar"))
        self.assertTrue(self.m._match(b"one/two", b"*/*"))

    def test_match_partial_wildcards(self):
        self.assertTrue(self.m._match(b"one/*", b"one/two"))
        self.assertTrue(self.m._match(b"foo/bar", b"foo/*"))

        self.assertFalse(self.m._match(b"one/*", b"two/three"))
        self.assertFalse(self.m._match(b"foo/bar", b"bar/baz"))


class TestLanguageAccept(unittest.TestCase):
    def setUp(self):
        self.l = LanguageAccept()

    def test_simple_match(self):
        self.assertTrue(self.l._match(b"en-US", b"en-US"))

    def test_normalized_match(self):
        self.assertTrue(self.l._match(b"en_US", b"EN-us"))

    def test_wildcard_match(self):
        self.assertTrue(self.l._match(b"en-US", b"*"))


class TestCharsetAccept(unittest.TestCase):
    def setUp(self):
        self.c = CharsetAccept()

    def test_simple_match(self):
        self.assertTrue(self.c._match(b"utf-8", b"utf-8"))

    def test_normalize_match(self):
        self.assertTrue(self.c._match(b"utf-8", b"UTF8"))

    def test_wildcard_match(self):
        self.assertTrue(self.c._match(b"utf-8", b"*"))


class TestWSGIAcceptMixin(unittest.TestCase):
    def make_obj(self, types):
        class TestObject(object):
            accept_mimetypes = []

        self.o = TestObject()
        self.o.accept_mimetypes = types

    def test_accepts_json(self):
        self.make_obj([b'application/json'])
        self.assertTrue(WSGIAcceptMixin.accepts_json.__get__(self.o))

        self.make_obj([b'application/other'])
        self.assertFalse(WSGIAcceptMixin.accepts_json.__get__(self.o))

    def test_accepts_xhtml(self):
        self.make_obj([b'application/xml'])
        self.assertTrue(WSGIAcceptMixin.accepts_xhtml.__get__(self.o))

        self.make_obj([b'application/other'])
        self.assertFalse(WSGIAcceptMixin.accepts_xhtml.__get__(self.o))

    def test_accepts_xhtml(self):
        self.make_obj([b'text/html'])
        self.o.accepts_xhtml = False
        self.assertTrue(WSGIAcceptMixin.accepts_html.__get__(self.o))

        self.make_obj([b'text/plain'])
        self.o.accepts_xhtml = False
        self.assertFalse(WSGIAcceptMixin.accepts_html.__get__(self.o))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestAcceptList))
    suite.addTest(unittest.makeSuite(TestMIMEAccept))
    suite.addTest(unittest.makeSuite(TestLanguageAccept))
    suite.addTest(unittest.makeSuite(TestCharsetAccept))
    suite.addTest(unittest.makeSuite(TestWSGIAcceptMixin))

    return suite
