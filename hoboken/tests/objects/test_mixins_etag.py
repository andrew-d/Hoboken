# -*- coding: utf-8 -*-

import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.etag import *


class TestMatchAnyEtag(unittest.TestCase):
    def setUp(self):
        self.e = MatchAnyEtag

    def test_will_match_anything(self):
        self.assertTrue('foobar' in self.e)

    def test_converts_to_str(self):
        self.assertEqual(str(self.e), '*')

    def test_is_false_boolean(self):
        self.assertFalse(bool(self.e))


class TestMatchNoneEtag(unittest.TestCase):
    def setUp(self):
        self.e = MatchNoneEtag

    def test_will_match_nothing(self):
        self.assertFalse('foobar' in self.e)

    def test_converts_to_str(self):
        self.assertEqual(str(self.e), '')

    def test_is_false_boolean(self):
        self.assertFalse(bool(self.e))


class TestWSGIRequestEtagMixin(unittest.TestCase):
    def setUp(self):
        self.m = WSGIRequestEtagMixin()
        self.m.headers = {}
        self.m.method = 'GET'

    def test_if_match_missing(self):
        self.assertEqual(self.m.if_match, MatchAnyEtag)

    def test_if_match_single(self):
        self.m.headers['If-Match'] = b'"foobar"'
        self.assertEqual(self.m.if_match, (b'foobar',))

    def test_if_match_multiple(self):
        self.m.headers['If-Match'] = b'"foobar", "asdf", "another"'
        self.assertEqual(self.m.if_match, (b'foobar', b'asdf', b'another'))

    def test_if_match_multiple_with_weak(self):
        self.m.headers['If-Match'] = b'W/"foobar", "asdf", W/"another"'
        self.assertEqual(self.m.if_match, (b'asdf',))

    def test_if_match_multiple_with_quoted(self):
        self.m.headers['If-Match'] = b'"foobar", "a\\"s\\"df", "another"'
        self.assertEqual(self.m.if_match, (b'foobar', b'a"s"df', b'another'))

    def test_if_match_multiple_with_wildcard(self):
        self.m.headers['If-Match'] = b'*'
        self.assertEqual(self.m.if_match, MatchAnyEtag)

    def test_if_none_match_missing(self):
        self.assertEqual(self.m.if_none_match, MatchNoneEtag)

    def test_if_none_match_single(self):
        self.m.headers['If-None-Match'] = b'"foobar"'
        self.assertEqual(self.m.if_none_match, (b'foobar',))

    def test_if_none_match_methods(self):
        self.m.headers['If-None-Match'] = b'"foobar", W/"asdf"'

        # Weak comparison works with GET / HEAD...
        for meth in ['GET', 'HEAD']:
            self.m.method = meth

            self.assertEqual(self.m.if_none_match, (b'foobar', b'asdf'))

        # ... but should not work for other methods.
        for meth in ['POST', 'PUT', 'PATCH', 'DELETE']:
            self.m.method = meth

            self.assertEqual(self.m.if_none_match, (b'foobar',))

    # NOTE: We don't need to test the rest of If-None-Match since it uses the
    # same parsing function as If-Match


class TestWSGIResponseEtagMixin(unittest.TestCase):
    def setUp(self):
        self.m = WSGIResponseEtagMixin()
        self.m.headers = {}

    def test_etag_empty(self):
        self.assertEqual(self.m.etag, None)

    def test_etag_strong(self):
        self.m.headers['Etag'] = b'"Foobar"'
        self.assertEqual(self.m.etag, (b'Foobar', True))

    def test_etag_weak(self):
        self.m.headers['Etag'] = b'W/"Foobar"'
        self.assertEqual(self.m.etag, (b'Foobar', False))

        self.m.headers['Etag'] = b'w/"Foobar"'
        self.assertEqual(self.m.etag, (b'Foobar', False))

    def test_set_etag(self):
        self.m.etag = b'SomeEtag'
        self.assertEqual(self.m.headers['Etag'], b'"SomeEtag"')

    def test_set_etag_quotes(self):
        self.m.etag = b'Some"Quoted"Etag'
        self.assertEqual(self.m.headers['Etag'], b'"Some\\"Quoted\\"Etag"')

    def test_set_etag_weak(self):
        self.m.etag = (b'Foobar', False)
        self.assertEqual(self.m.etag[1], False)
        self.assertTrue(self.m.headers['Etag'].startswith(b'W/'))

    def test_no_etag_match(self):
        self.m.headers['Etag'] = b'NO_MATCH"'
        self.assertEqual(self.m.etag, b'NO_MATCH"')

    def test_set_invalid_etag(self):
        with self.assertRaises(ValueError):
            self.m.etag = 123

    def test_set_existing_etag(self):
        self.m.etag = b'W/"foobar"'
        self.assertEqual(self.m.etag, (b'foobar', False))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMatchAnyEtag))
    suite.addTest(unittest.makeSuite(TestMatchNoneEtag))
    suite.addTest(unittest.makeSuite(TestWSGIRequestEtagMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseEtagMixin))

    return suite

