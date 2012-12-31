# -*- coding: utf-8 -*-

from hoboken.tests.compat import unittest
from mock import Mock

from hoboken.objects.util import *
from hoboken.objects.util import _int_parser


class TestEnvironPropWithDefault(unittest.TestCase):
    def setUp(self):
        self.default = object()

        class TestClass(object):
            _from_wsgi_str = Mock(side_effect=lambda x: x)
            _to_wsgi_str = Mock(side_effect=lambda x: x)

            environ = {'prop': 'value'}

            prop = _environ_prop('prop', default=self.default)

        self.TestClass = TestClass
        self.cls = TestClass()

    def test_getter_works(self):
        self.assertEqual(self.cls.prop, 'value')

    def test_setter_works(self):
        self.cls.prop = 'foo'
        self.assertEqual(self.cls.prop, 'foo')

    def test_will_call_from_wsgi_str(self):
        v = self.cls.prop
        self.cls._from_wsgi_str.assert_called_with('value')

    def test_will_call_to_wsgi_str(self):
        self.cls.prop = 'input'
        self.cls._to_wsgi_str.assert_called_with('input')

    def test_will_return_default(self):
        del self.cls.environ['prop']
        self.assertEqual(self.cls.prop, self.default)

    def test_will_remove_on_None_set(self):
        self.cls.prop = None
        self.assertNotIn('prop', self.cls.environ)

    def test_will_delete(self):
        del self.cls.prop
        self.assertNotIn('prop', self.cls.environ)


class TestEnvironPropWithoutDefault(unittest.TestCase):
    def setUp(self):
        class TestClass(object):
            _from_wsgi_str = Mock(side_effect=lambda x: x)
            _to_wsgi_str = Mock(side_effect=lambda x: x)

            environ = {'prop': 'value'}

            prop = _environ_prop('prop')

        self.TestClass = TestClass
        self.cls = TestClass()

    def test_getter_works(self):
        self.assertEqual(self.cls.prop, 'value')

    def test_setter_works(self):
        self.cls.prop = 'foo'
        self.assertEqual(self.cls.prop, 'foo')

    def test_will_call_from_wsgi_str(self):
        v = self.cls.prop
        self.cls._from_wsgi_str.assert_called_with('value')

    def test_will_call_to_wsgi_str(self):
        self.cls.prop = 'input'
        self.cls._to_wsgi_str.assert_called_with('input')

    def test_deletion_will_fail(self):
        with self.assertRaises(AttributeError):
            del self.cls.prop


class TestEnvironConverter(unittest.TestCase):
    def setUp(self):
        class TestClass(object):
            parser = Mock(side_effect=lambda x: x)
            serializer = Mock(side_effect=lambda x: x)

            prop_get = Mock(return_value='foo')
            prop_set = Mock()
            prop_del = Mock()

            prop = property(prop_get, prop_set, prop_del)

            conv = _environ_converter(prop, parser, serializer)

        self.TestClass = TestClass
        self.cls = TestClass()

    def test_getter_is_called(self):
        v = self.cls.conv
        self.cls.prop_get.assert_called_once_with(self.cls)

    def test_setter_is_called(self):
        self.cls.conv = 'foo'
        self.cls.prop_set.assert_called_once_with(self.cls, 'foo')

    def test_deleter_is_called(self):
        del self.cls.conv
        self.cls.prop_del.assert_called_once_with(self.cls)

    def test_parser_called_on_get(self):
        v = self.cls.conv
        self.cls.parser.assert_called_once_with('foo')

    def test_serializer_called_on_set(self):
        self.cls.conv = 'foo'
        self.cls.serializer.assert_called_once_with('foo')

    def test_serializer_not_called_with_None(self):
        self.cls.conv = None
        self.assertFalse(self.cls.serializer.called)


class TestCachedProperty(unittest.TestCase):
    def setUp(self):
        self.calls = 0

        class TestClass(object):
            @cached_property
            def cache(blah):
                self.calls += 1
                return 123

        self.TestClass = TestClass
        self.cls = TestClass()

    def test_will_cache(self):
        self.assertEqual(self.cls.cache, 123)
        self.assertEqual(self.calls, 1)

        val = self.cls.cache

        self.assertEqual(self.calls, 1)

    def test_can_be_set(self):
        self.assertEqual(self.cls.cache, 123)
        self.cls.cache = 456
        self.assertEqual(self.cls.cache, 456)

    def test_get_from_class(self):
        self.assertTrue(isinstance(self.TestClass.cache, cached_property))


class TestBytesIteratorFile(unittest.TestCase):
    def setUp(self):
        self.f = BytesIteratorFile([b'foo', b'bar', b'baz'])

    def test_readall(self):
        self.assertEqual(self.f.readall(), b'foobarbaz')

    def test_read_single_chunk(self):
        self.assertEqual(self.f.read(3), b'foo')

    def test_read_chunk_and_a_half(self):
        self.assertEqual(self.f.read(4), b'foob')

    def test_read_with_cache(self):
        self.assertEqual(self.f.read(4), b'foob')
        self.assertEqual(self.f.read(2), b'ar')

    def test_read_three_chunks(self):
        self.assertEqual(self.f.read(9), b'foobarbaz')

    def test_read_past_end(self):
        self.assertEqual(self.f.read(9), b'foobarbaz')
        self.assertEqual(self.f.read(2), b'')
        self.assertEqual(self.f.read(1), b'')

    def test_read_with_all(self):
        self.assertEqual(self.f.read(-1), b'foobarbaz')


class TestOther(unittest.TestCase):
    def test_int_parser_handles_invalid(self):
        self.assertIs(_int_parser(None), None)
        self.assertIs(_int_parser(b''), None)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestEnvironPropWithDefault))
    suite.addTest(unittest.makeSuite(TestEnvironPropWithoutDefault))
    suite.addTest(unittest.makeSuite(TestEnvironConverter))
    suite.addTest(unittest.makeSuite(TestCachedProperty))
    suite.addTest(unittest.makeSuite(TestBytesIteratorFile))
    suite.addTest(unittest.makeSuite(TestOther))

    return suite

