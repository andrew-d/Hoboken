# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.etag import *


class TestMatchAnyEtag(BaseTestCase):
    def setup(self):
        self.e = MatchAnyEtag

    def test_will_match_anything(self):
        self.assert_true('foobar' in self.e)

    def test_converts_to_str(self):
        self.assert_equal(str(self.e), '*')

    def test_is_false_boolean(self):
        self.assert_false(bool(self.e))


class TestMatchNoneEtag(BaseTestCase):
    def setup(self):
        self.e = MatchNoneEtag

    def test_will_match_nothing(self):
        self.assert_false('foobar' in self.e)

    def test_converts_to_str(self):
        self.assert_equal(str(self.e), '')

    def test_is_false_boolean(self):
        self.assert_false(bool(self.e))


class TestWSGIRequestEtagMixin(BaseTestCase):
    def setup(self):
        self.m = WSGIRequestEtagMixin()
        self.m.headers = {}
        self.m.method = 'GET'

    def test_if_match_missing(self):
        self.assert_equal(self.m.if_match, MatchAnyEtag)

    def test_if_match_single(self):
        self.m.headers['If-Match'] = b'"foobar"'
        self.assert_equal(self.m.if_match, (b'foobar',))

    def test_if_match_multiple(self):
        self.m.headers['If-Match'] = b'"foobar", "asdf", "another"'
        self.assert_equal(self.m.if_match, (b'foobar', b'asdf', b'another'))

    def test_if_match_multiple_with_weak(self):
        self.m.headers['If-Match'] = b'W/"foobar", "asdf", W/"another"'
        self.assert_equal(self.m.if_match, (b'asdf',))

    def test_if_match_multiple_with_quoted(self):
        self.m.headers['If-Match'] = b'"foobar", "a\\"s\\"df", "another"'
        self.assert_equal(self.m.if_match, (b'foobar', b'a"s"df', b'another'))

    def test_if_match_multiple_with_wildcard(self):
        self.m.headers['If-Match'] = b'*'
        self.assert_equal(self.m.if_match, MatchAnyEtag)

    def test_if_none_match_missing(self):
        self.assert_equal(self.m.if_none_match, MatchNoneEtag)

    def test_if_none_match_single(self):
        self.m.headers['If-None-Match'] = b'"foobar"'
        self.assert_equal(self.m.if_none_match, (b'foobar',))

    def test_if_none_match_methods(self):
        self.m.headers['If-None-Match'] = b'"foobar", W/"asdf"'

        # Weak comparison works with GET / HEAD...
        for meth in ['GET', 'HEAD']:
            self.m.method = meth

            self.assert_equal(self.m.if_none_match, (b'foobar', b'asdf'))

        # ... but should not work for other methods.
        for meth in ['POST', 'PUT', 'PATCH', 'DELETE']:
            self.m.method = meth

            self.assert_equal(self.m.if_none_match, (b'foobar',))

    # NOTE: We don't need to test the rest of If-None-Match since it uses the
    # same parsing function as If-Match


class TestWSGIResponseEtagMixin(BaseTestCase):
    def setup(self):
        self.m = WSGIResponseEtagMixin()
        self.m.headers = {}

    def test_etag_empty(self):
        self.assert_equal(self.m.etag, None)

    def test_etag_strong(self):
        self.m.headers['Etag'] = b'"Foobar"'
        self.assert_equal(self.m.etag, (b'Foobar', True))

    def test_etag_weak(self):
        self.m.headers['Etag'] = b'W/"Foobar"'
        self.assert_equal(self.m.etag, (b'Foobar', False))

        self.m.headers['Etag'] = b'w/"Foobar"'
        self.assert_equal(self.m.etag, (b'Foobar', False))

    # TODO: make these work
    # def test_etag_unquoted(self):
    #     self.m.headers['Etag'] = b'Foobar'
    #     self.assert_equal(self.m.etag, (b'Foobar', True))

    #     self.m.headers['Etag'] = b'W/Foobar'
    #     self.assert_equal(self.m.etag, (b'Foobar', False))

    def test_set_etag(self):
        self.m.etag = b'SomeEtag'
        self.assert_equal(self.m.headers['Etag'], b'"SomeEtag"')

    def test_set_etag_quotes(self):
        self.m.etag = b'Some"Quoted"Etag'
        self.assert_equal(self.m.headers['Etag'], b'"Some\\"Quoted\\"Etag"')

    def test_set_etag_weak(self):
        self.m.etag = (b'Foobar', False)
        self.assert_equal(self.m.etag[1], False)
        self.assert_true(self.m.headers['Etag'].startswith(b'W/'))

    def test_no_etag_match(self):
        self.m.headers['Etag'] = b'NO_MATCH"'
        self.assert_equal(self.m.etag, b'NO_MATCH"')

    def test_set_invalid_etag(self):
        with self.assert_raises(ValueError):
            self.m.etag = 123

    def test_set_existing_etag(self):
        self.m.etag = b'W/"foobar"'
        self.assert_equal(self.m.etag, (b'foobar', False))


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMatchAnyEtag))
    suite.addTest(unittest.makeSuite(TestMatchNoneEtag))
    suite.addTest(unittest.makeSuite(TestWSGIRequestEtagMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseEtagMixin))

    return suite

