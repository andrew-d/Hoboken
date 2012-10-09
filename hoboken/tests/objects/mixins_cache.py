# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.cache import *


class TestCacheObject(BaseTestCase):
    pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestCacheObject))

    return suite
