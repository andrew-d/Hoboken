# -*- coding: utf-8 -*-

from . import BaseTestCase
import unittest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.cache import *
from hoboken.objects.mixins.cache import _boolean_property, _value_property


class TestBooleanProperty(BaseTestCase):
    def setup(self):
        self.p = _boolean_property('name')
        self.o = Mock()
        self.o.get_property.return_value = "foo"
        self.o.set_property.return_value = None

    def test_get(self):
        self.assert_equal(_boolean_property.__get__(self.p, self.o), "foo")
        self.o.get_property.assert_called_once_with("name")

    def test_get_with_None(self):
        self.o.get_property.return_value = None
        self.assert_equal(_boolean_property.__get__(self.p, self.o), False)
        self.o.get_property.assert_called_once_with("name")

    def test_set(self):
        _boolean_property.__set__(self.p, self.o, 'value')
        self.o.set_property.assert_called_once_with('name', 'value')

    def test_delete(self):
        _boolean_property.__delete__(self.p, self.o)
        self.o.set_property.assert_called_once_with('name', False)


class TestValueProperty(BaseTestCase):
    def setup(self):
        self.p = _value_property('name')
        self.o = Mock()
        self.o.get_property.return_value = "foo"
        self.o.set_property.return_value = None

    def test_get(self):
        self.assert_equal(_value_property.__get__(self.p, self.o), "foo")
        self.o.get_property.assert_called_once_with("name")

    def test_set(self):
        _value_property.__set__(self.p, self.o, 'value')
        self.o.set_property.assert_called_once_with('name', 'value')

    def test_delete(self):
        _value_property.__delete__(self.p, self.o)
        self.o.set_property.assert_called_once_with('name', None)


class TestCacheObject(BaseTestCase):
    def test_parse_value(self):
        props = CacheObject.parse_value("no-cache, no-store, max-age=123")
        self.assert_equal(props, {"no-cache": True, "no-store": True, "max-age": 123})

    def test_parse(self):
        http_obj = object()
        o = CacheObject.parse(http_obj, "no-cache, no-store, max-age=123")
        self.assert_is_instance(o, CacheObject)

    def test_serialize_cache_control(self):
        m = CacheObject(None, initial_properties={
            "no-cache": True,
            "no-store": True,
            "max-age": 123,
        })
        self.assert_equal(m._serialize_cache_control(), "max-age=123, no-cache, no-store")

        n = CacheObject(None, initial_properties={'quoted': 'foo and bar'})
        self.assert_equal(n._serialize_cache_control(), 'quoted="foo and bar"')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBooleanProperty))
    suite.addTest(unittest.makeSuite(TestValueProperty))
    suite.addTest(unittest.makeSuite(TestCacheObject))

    return suite
