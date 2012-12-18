# -*- coding: utf-8 -*-

import unittest
from mock import Mock

from hoboken.objects.http import *
from hoboken.six import u


class TestQuote(unittest.TestCase):
    def test_with_unicode(self):
        val = b'\xe2\x88\x91'.decode('utf-8')   # \u2211, sum character
        enc = quote(val)

        self.assertEqual(enc, b'%E2%88%91')

    def test_unsafe_re(self):
        unsafe = u('[a-z]')
        enc = quote('aSDF', unsafe=unsafe)
        self.assertEqual(enc, b'%61SDF')


class TestUnquote(unittest.TestCase):
    def test_basic(self):
        val = b'\xe2\x88\x91'                   # \u2211, sum character
        de = unquote(b'%E2%88%91')
        self.assertEqual(de, val)

    def test_with_unicode(self):
        val = b'%61SDF'.decode('latin-1')
        de = unquote(val)
        self.assertEqual(de, b'aSDF')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestQuote))
    suite.addTest(unittest.makeSuite(TestUnquote))

    return suite

