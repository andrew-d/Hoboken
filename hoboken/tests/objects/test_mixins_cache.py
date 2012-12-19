# -*- coding: utf-8 -*-

import unittest

import pytest
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.cache import *
from hoboken.objects.mixins.cache import _boolean_property, _value_property


class TestBooleanProperty(unittest.TestCase):
    def setUp(self):
        self.p = _boolean_property('name')
        self.o = Mock()
        self.o.get_property.return_value = "foo"
        self.o.set_property.return_value = None

    def test_get(self):
        self.assertEqual(_boolean_property.__get__(self.p, self.o), "foo")
        self.o.get_property.assert_called_once_with("name")

    def test_get_with_None(self):
        self.o.get_property.return_value = None
        self.assertEqual(_boolean_property.__get__(self.p, self.o), False)
        self.o.get_property.assert_called_once_with("name")

    def test_set(self):
        _boolean_property.__set__(self.p, self.o, True)
        self.o.set_property.assert_called_once_with('name', True)

    def test_delete(self):
        _boolean_property.__delete__(self.p, self.o)
        self.o.set_property.assert_called_once_with('name', False)

    def test_bad_set(self):
        with self.assertRaises(ValueError):
            _boolean_property.__set__(self.p, self.o, 'bad')


class TestValueProperty(unittest.TestCase):
    def setUp(self):
        self.p = _value_property('name')
        self.o = Mock()
        self.o.get_property.return_value = "foo"
        self.o.set_property.return_value = None

    def test_get(self):
        self.assertEqual(_value_property.__get__(self.p, self.o), "foo")
        self.o.get_property.assert_called_once_with("name")

    def test_set(self):
        _value_property.__set__(self.p, self.o, 'value')
        self.o.set_property.assert_called_once_with('name', 'value')

    def test_delete(self):
        _value_property.__delete__(self.p, self.o)
        self.o.set_property.assert_called_once_with('name', None)


class TestCacheObject(unittest.TestCase):
    def test_parse_value(self):
        props = CacheObject.parse_value(b"no-cache, no-store, max-age=123")
        self.assertEqual(props,
            {b"no-cache": True, b"no-store": True, b"max-age": 123}
        )

    def test_parse(self):
        http_obj = object()
        o = CacheObject.parse(http_obj, b"no-cache, no-store, max-age=123")
        self.assertTrue(isinstance(o, CacheObject))

    def test_serialize_cache_control(self):
        m = CacheObject(None, initial_properties={
            b"no-cache": True,
            b"no-store": True,
            b"max-age": 123,
        })
        self.assertEqual(m._serialize_cache_control(),
                          b"max-age=123, no-cache, no-store")

        n = CacheObject(None, initial_properties={b'quoted': b'foo and bar'})
        self.assertEqual(n._serialize_cache_control(),
                          b'quoted="foo and bar"')

    def test_serialize_cache_control_unicode(self):
        val = b'foobar'.decode('latin-1')
        m = CacheObject(None, initial_properties={
            b'no-cache': val
        })
        self.assertEqual(m._serialize_cache_control(), b'no-cache=foobar')

    def test_reparse(self):
        class tmp(object):
            headers = {}

        t = tmp()
        c = CacheObject.parse(t, b'no-cache')
        self.assertEqual(c.get_property(b'no-cache'), True)
        self.assertTrue(c.get_property(b'no-store') is None)

        t.headers['Cache-Control'] = b'no-store'
        c.reparse()
        self.assertEqual(c.get_property(b'no-store'), True)
        self.assertTrue(c.get_property(b'no-cache') is None)

    def test_parse_invalid(self):
        c = CacheObject.parse({}, b'max-age=12a3, no-store')
        self.assertEqual(c.get_property(b'max-age'), b'12a3')


class TestWSGIRequestCacheMixin(object):
    BOOLEAN_PROPS = ['no_cache', 'no_store', 'no_transform', 'only_if_cached']
    VALUE_PROPS = ['max_age', 'max_stale', 'min_fresh']

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.r = WSGIRequestCacheMixin()
        self.r.headers = {}

    def test_cache_control(self):
        assert isinstance(self.r.cache_control, RequestCacheObject)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_get_boolean_properties(self, param_name):
        assert not getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_set_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        assert getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_del_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        delattr(self.r.cache_control, param_name)
        assert not getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_get_value_properties(self, param_name):
        assert getattr(self.r.cache_control, param_name) is None

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_set_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        assert getattr(self.r.cache_control, param_name) == b'some_value'

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_del_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        delattr(self.r.cache_control, param_name)
        assert getattr(self.r.cache_control, param_name) is None


class TestWSGIResponseCacheMixin(object):
    BOOLEAN_PROPS = ['public', 'no_store', 'no_transform',
                     'must_revalidate', 'proxy_revalidate']
    VALUE_PROPS = ['no_cache', 'private', 'max_age', 's_max_age',
                   's_maxage']

    @pytest.fixture(autouse=True)
    def setUp(self):
        self.r = WSGIResponseCacheMixin()
        self.r.headers = {}

    def test_cache_control(self):
        assert isinstance(self.r.cache_control, ResponseCacheObject)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_get_boolean_properties(self, param_name):
        assert not getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_set_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        assert getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', BOOLEAN_PROPS)
    def test_del_boolean_properties(self, param_name):
        setattr(self.r.cache_control, param_name, True)
        delattr(self.r.cache_control, param_name)
        assert not getattr(self.r.cache_control, param_name)

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_get_value_properties(self, param_name):
        assert getattr(self.r.cache_control, param_name) is None

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_set_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        assert getattr(self.r.cache_control, param_name) == b'some_value'

    @pytest.mark.parametrize('param_name', VALUE_PROPS)
    def test_del_value_properties(self, param_name):
        setattr(self.r.cache_control, param_name, b'some_value')
        delattr(self.r.cache_control, param_name)
        assert getattr(self.r.cache_control, param_name) is None

    def test_s_maxage_variants(self):
        self.r.cache_control.s_max_age = True
        assert self.r.cache_control.s_maxage

        self.r.cache_control.s_maxage = False
        assert not self.r.cache_control.s_max_age


class TestWSGIResponseOtherCachesMixin(unittest.TestCase):
    def setUp(self):
        self.r = WSGIResponseOtherCachesMixin()
        self.r.headers = {}

    def test_age_simple(self):
        self.assertEqual(self.r.age, None)
        self.r.age = 123
        self.assertEqual(self.r.age, 123)

    def test_age_with_bytes(self):
        self.r.age = b'123'
        self.assertEqual(self.r.age, 123)

    def test_age_with_invalid(self):
        self.r.headers['Age'] = b'bad data'
        self.assertTrue(self.r.age is None)


class TestPragmaNoCacheMixin(unittest.TestCase):
    def setUp(self):
        self.calls = 0
        self.val = None

        class HttpObj(object):
            headers = {}

        class Base(object):
            http_obj = None

            @property
            def no_cache(this):
                self.calls += 1
                return self.val

        class MixedIn(PragmaNoCacheMixin, Base):
            pass

        self.c = MixedIn()
        self.h = HttpObj()
        self.c.http_obj = self.h

    def test_will_override(self):
        self.h.headers['Pragma'] = b'no-cache'
        self.assertTrue(self.c.no_cache)
        self.assertEqual(self.calls, 1)

    def test_will_not_override_if_given(self):
        self.val = False
        self.assertFalse(self.c.no_cache)
        self.assertEqual(self.calls, 1)

    def test_will_ignore_invalid(self):
        self.h.headers['Pragma'] = b'some-other-val'
        self.assertTrue(self.c.no_cache is None)
        self.assertEqual(self.calls, 1)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestBooleanProperty))
    suite.addTest(unittest.makeSuite(TestValueProperty))
    suite.addTest(unittest.makeSuite(TestCacheObject))
    # suite.addTest(unittest.makeSuite(TestWSGIRequestCacheMixin))
    # suite.addTest(unittest.makeSuite(TestWSGIResponseCacheMixin))
    suite.addTest(unittest.makeSuite(TestWSGIResponseOtherCachesMixin))
    suite.addTest(unittest.makeSuite(TestPragmaNoCacheMixin))

    return suite
