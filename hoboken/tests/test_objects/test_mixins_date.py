# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.date import *


class TestWSGIResponseDateMixin(BaseTestCase):
    def setup(self):
        self.d = WSGIResponseDateMixin()
        self.d.headers = {}


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestWSGIResponseDateMixin))

    return suite
