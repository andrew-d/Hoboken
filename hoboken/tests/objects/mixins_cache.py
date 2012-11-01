# -*- coding: utf-8 -*-

from . import BaseTestCase
from hoboken.tests.helpers import parameters, parametrize
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
        _boolean_property.__set__(self.p, self.o, True)
        self.o.set_property.assert_called_once_with('name', True)

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
        props = CacheObject.parse_value(b"no-cache, no-store, max-age=123")
        self.assert_equal(props, {b"no-cache": True, b"no-store": True, b"max-age": 123})

    def test_parse(self):
        http_obj = object()
        o = CacheObject.parse(http_obj, b"no-cache, no-store, max-age=123")
        self.assert_is_instance(o, CacheObject)

    def test_serialize_cache_control(self):
        m = CacheObject(None, initial_properties={
            b"no-cache": True,
            b"no-store": True,
            b"max-age": 123,
        })
        self.assert_equal(m._serialize_cache_control(), b"max-age=123, no-cache, no-store")

        n = CacheObject(None, initial_properties={b'quoted': b'foo and bar'})
        self.assert_equal(n._serialize_cache_control(), b'quoted="foo and bar"')


@parametrize
class TestWSGIRequestCacheMixin(BaseTestCase):
    BOOLEAN_PROPS = ['no_cache', 'no_store', 'no_transform', 'only_if_cached']
    VALUE_PROPS = ['max_age', 'max_stale', 'min_fresh']

    def setup(self):
        self.r = WSGIRequestCacheMixin()
        self.r.headers = {}

    def test_cache_control(self):
        self.assert_is_instance(self.r.cache_control, RequestCacheObject)

    @parameters(BOOLEAN_PROPS)
    def test_get_boolean_properties(self, param_name):
        self.assert_false(getattr(self.r.cache_control, param_name))

    @parameters(BOOLEAN_PROPS)
    def test_set_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        self.assert_true(getattr(self.r.cache_control, param_name))

    @parameters(BOOLEAN_PROPS)
    def test_del_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        delattr(self.r.cache_control, param_name)
        self.assert_false(getattr(self.r.cache_control, param_name))

    @parameters(VALUE_PROPS)
    def test_get_value_properties(self, param_name):
        self.assert_true(getattr(self.r.cache_control, param_name) is None)

    @parameters(VALUE_PROPS)
    def test_set_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, 'some_value')
        self.assert_equal(getattr(self.r.cache_control, param_name), 'some_value')

    @parameters(VALUE_PROPS)
    def test_del_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, 'some_value')
        delattr(self.r.cache_control, param_name)
        self.assert_true(getattr(self.r.cache_control, param_name) is None)



class TestWSGIResponseCacheMixin(BaseTestCase):
    def test_cache_control(self):
        r = WSGIResponseCacheMixin()
        r.headers = {}
        self.assert_is_instance(r.cache_control, ResponseCacheObject)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBooleanProperty))
    suite.addTest(unittest.makeSuite(TestValueProperty))
    suite.addTest(unittest.makeSuite(TestCacheObject))
    suite.addTest(unittest.makeSuite(TestWSGIRequestCacheMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseCacheMixin))

    return suite
