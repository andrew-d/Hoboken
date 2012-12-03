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

    def test_bad_set(self):
        with self.assert_raises(ValueError):
            _boolean_property.__set__(self.p, self.o, 'bad')


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
        self.assert_equal(props,
            {b"no-cache": True, b"no-store": True, b"max-age": 123}
        )

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
        self.assert_equal(m._serialize_cache_control(),
                          b"max-age=123, no-cache, no-store")

        n = CacheObject(None, initial_properties={b'quoted': b'foo and bar'})
        self.assert_equal(n._serialize_cache_control(),
                          b'quoted="foo and bar"')

    def test_reparse(self):
        class tmp(object):
            headers = {}

        t = tmp()
        c = CacheObject.parse(t, b'no-cache')
        self.assert_equal(c.get_property(b'no-cache'), True)
        self.assert_true(c.get_property(b'no-store') is None)

        t.headers['Cache-Control'] = b'no-store'
        c.reparse()
        self.assert_equal(c.get_property(b'no-store'), True)
        self.assert_true(c.get_property(b'no-cache') is None)


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
        setattr(self.r.cache_control, param_name, b'some_value')
        self.assert_equal(getattr(self.r.cache_control, param_name),
                          b'some_value')

    @parameters(VALUE_PROPS)
    def test_del_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        delattr(self.r.cache_control, param_name)
        self.assert_true(getattr(self.r.cache_control, param_name) is None)

@parametrize
class TestWSGIResponseCacheMixin(BaseTestCase):
    BOOLEAN_PROPS = ['public', 'no_store', 'no_transform',
                     'must_revalidate', 'proxy_revalidate']
    VALUE_PROPS = ['no_cache', 'private', 'max_age', 's_max_age',
                   's_maxage']

    def setup(self):
        self.r = WSGIResponseCacheMixin()
        self.r.headers = {}

    def test_cache_control(self):
        self.assert_is_instance(self.r.cache_control, ResponseCacheObject)

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
        setattr(self.r.cache_control, param_name, b'some_value')
        self.assert_equal(getattr(self.r.cache_control, param_name),
                          b'some_value')

    @parameters(VALUE_PROPS)
    def test_del_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        delattr(self.r.cache_control, param_name)
        self.assert_true(getattr(self.r.cache_control, param_name) is None)

    def test_s_maxage_variants(self):
        self.r.cache_control.s_max_age = True
        self.assert_true(self.r.cache_control.s_maxage)

        self.r.cache_control.s_maxage = False
        self.assert_false(self.r.cache_control.s_max_age)


class TestWSGIResponseOtherCachesMixin(BaseTestCase):
    def setup(self):
        self.r = WSGIResponseOtherCachesMixin()
        self.r.headers = {}

    def test_age_simple(self):
        self.assert_equal(self.r.age, None)
        self.r.age = 123
        self.assert_equal(self.r.age, 123)

    def test_age_with_bytes(self):
        self.r.age = b'123'
        self.assert_equal(self.r.age, 123)

    def test_age_with_invalid(self):
        self.r.headers['Age'] = b'bad data'
        self.assert_true(self.r.age is None)



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBooleanProperty))
    suite.addTest(unittest.makeSuite(TestValueProperty))
    suite.addTest(unittest.makeSuite(TestCacheObject))
    suite.addTest(unittest.makeSuite(TestWSGIRequestCacheMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseCacheMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseOtherCachesMixin))

    return suite
