# -*- coding: utf-8 -*-

import copy
import pickle
import contextlib
import collections
from io import BytesIO
from hoboken.tests.compat import unittest, xfail
from mock import Mock

from hoboken.objects.datastructures import *
from hoboken.six import PY3


class TestImmutableList(unittest.TestCase):
    def setUp(self):
        self.l = ImmutableList(range(10))

    def test_delete_item(self):
        with self.assertRaises(TypeError):
            del self.l[0]

        with self.assertRaises(TypeError):
            del self.l[0:2]

    def test_set_item(self):
        with self.assertRaises(TypeError):
            self.l[0] = 1

        with self.assertRaises(TypeError):
            self.l[0:2] = [1, 2]

    def test_operators(self):
        with self.assertRaises(TypeError):
            self.l += [10, 11, 12]

        with self.assertRaises(TypeError):
            self.l *= 2

    def test_insertion_functions(self):
        with self.assertRaises(TypeError):
            self.l.append(1)

        with self.assertRaises(TypeError):
            self.l.insert(0, 1)

        with self.assertRaises(TypeError):
            self.l.extend([10, 11, 12])

    def test_removal_functions(self):
        with self.assertRaises(TypeError):
            self.l.remove(1)

        with self.assertRaises(TypeError):
            self.l.pop()

    def test_misc_functions(self):
        with self.assertRaises(TypeError):
            self.l.reverse()

        with self.assertRaises(TypeError):
            self.l.sort()

    def test_is_hashable(self):
        h = hash(self.l)
        self.assertIsNotNone(h)
        self.assertEqual(hash(self.l), h)

    def test_is_picklable(self):
        dst = BytesIO()
        p = pickle.Pickler(dst)
        p.dump(self.l)

        data = dst.getvalue()
        src = BytesIO(data)
        u = pickle.Unpickler(src)
        j = u.load()

        self.assertEqual(self.l, j)


class TestImmutableDict(unittest.TestCase):
    def setUp(self):
        self.d = ImmutableDict({'a': 'b', 'c': 'd'})

    def test_delete_item(self):
        with self.assertRaises(TypeError):
            del self.d['a']

    def test_set_item(self):
        with self.assertRaises(TypeError):
            self.d['a'] = 1

    def test_update(self):
        with self.assertRaises(TypeError):
            self.d.update({'e': 'f'})

    def test_pop(self):
        with self.assertRaises(TypeError):
            self.d.pop('a')

    def test_popitem(self):
        with self.assertRaises(TypeError):
            self.d.popitem()

    def test_clear(self):
        with self.assertRaises(TypeError):
            self.d.clear()

    def test_setdefault(self):
        with self.assertRaises(TypeError):
            self.d.setdefault('e', 'f')

    def test_fromkeys(self):
        d = ImmutableDict.fromkeys([1, 2, 3])
        self.assertEqual(list(d.keys()), [1, 2, 3])

    def test_is_hashable(self):
        h = hash(self.d)
        self.assertIsNotNone(h)
        self.assertEqual(hash(self.d), h)

    def test_copy(self):
        self.assertTrue(isinstance(self.d.copy(), dict))

    def test_copy_module(self):
        c = copy.copy(self.d)
        self.assertIs(c, self.d)

    def test_is_picklable(self):
        dst = BytesIO()
        p = pickle.Pickler(dst)
        p.dump(self.d)

        data = dst.getvalue()
        src = BytesIO(data)
        u = pickle.Unpickler(src)
        j = u.load()

        self.assertEqual(self.d, j)


class TestConvertingDict(unittest.TestCase):
    def setUp(self):
        self.d = ConvertingDict({'a': '1', 'b': 2})

    def test_get_with_default(self):
        self.assertEqual(self.d.get('a'), '1')

    def test_get_error(self):
        self.assertEqual(self.d.get('q', default=3), 3)

    def test_get_with_type(self):
        v = self.d.get('a', type=int)
        self.assertEqual(v, 1)


class TestImmutableConvertingDict(unittest.TestCase):
    def setUp(self):
        self.d = ImmutableConvertingDict({'a': '1', 'b': 2})

    def test_copy(self):
        self.assertTrue(isinstance(self.d.copy(), ConvertingDict))

    def test_copy_module(self):
        self.assertIs(copy.copy(self.d), self.d)


class TestIterMulti(unittest.TestCase):
    def assertm(self, mapping, l):
        self.assertEqual(list(iter_multi_items(mapping)), l)

    def test_with_multidict(self):
        m = MultiDict()
        m.add(1, 1)
        m.add(1, 2)
        m.add(1, 3)

        self.assertm(m, [(1, 1), (1, 2), (1, 3)])

    def test_with_dict(self):
        d = {1: 1, 2: 2, 3: 3}
        self.assertm(d, [(1, 1), (2, 2), (3, 3)])

    def test_with_dict_and_nested(self):
        d = {
            1: [1, 2],
            3: (4, 5),
        }
        self.assertm(d, [(1, 1), (1, 2), (3, 4), (3, 5)])

    def test_with_other_MutableMapping(self):
        d = CallbackDict({
            1: 1,
            2: 2
        })
        self.assertm(d, [(1, 1), (2, 2)])

    def test_with_other_iterable(self):
        l = [
            (1, 1),
            (2, 2),
            (3, 3),
        ]
        self.assertm(l, [(1, 1), (2, 2), (3, 3)])


class TestMultiDict(unittest.TestCase):
    def setUp(self):
        self.m = MultiDict({'a': 1, 'b': [2], 'c': [3, 4]})
        self.e = MultiDict()    # Empty dict.

    def assertm(self, val):
        self.assertEqual(self.m.to_dict(flat=False), val)

    def asserte(self, val):
        self.assertEqual(self.e.to_dict(flat=False), val)

    def test_default_value(self):
        self.asserte({})

    def test_dict_constructor(self):
        self.m = MultiDict({'a': 1, 'b': 2, 'c': 3})
        self.assertm({'a': [1], 'b': [2], 'c': [3]})

        self.m = MultiDict({'a': 1, 'b': [2, 3], 'c': (4, 5)})
        self.assertm({'a': [1], 'b': [2, 3], 'c': [4, 5]})

    def test_multidict_constructor(self):
        x = MultiDict({'a': [1, 2, 3], 'b': 4})
        self.m = MultiDict(x)

        self.assertm({'a': [1, 2, 3], 'b': [4]})

    def test_iterator_constructor(self):
        self.m = MultiDict([('a', 1), ('b', 2)])
        self.assertm({'a': [1], 'b': [2]})

    def test_fromkeys(self):
        self.m = MultiDict.fromkeys([1, 2, 3], 4)
        self.assertm({1: [4], 2: [4], 3: [4]})

    def test_is_picklable(self):
        dst = BytesIO()
        p = pickle.Pickler(dst)
        p.dump(self.m)

        data = dst.getvalue()
        src = BytesIO(data)
        u = pickle.Unpickler(src)
        j = u.load()

        self.assertEqual(self.m, j)

    def test_dict_getitem(self):
        self.assertEqual(self.m['a'], 1)
        self.assertEqual(self.m['b'], 2)
        self.assertEqual(self.m['c'], 3)

    def test_dict_setitem(self):
        self.m['c'] = 5
        self.assertm({'a': [1], 'b': [2], 'c': [5]})

    def test_setdefault(self):
        self.m.setdefault('d', 5)
        self.assertEqual(self.m['d'], 5)

        self.assertEqual(self.m.setdefault('a', 2), 1)

    def test_update_multidict(self):
        self.e.update(self.m)
        self.assertEqual(self.e, self.m)

    def test_update_dict(self):
        self.e.update({'a': 1, 'b': [2, 3], 'c': (4, 5)})
        self.asserte({'a': [1], 'b': [2, 3], 'c': [4, 5]})

    def test_update_iterator(self):
        self.e.update([('a', 1), ('b', 2)])
        self.asserte({'a': [1], 'b': [2]})

    def test_pop(self):
        self.assertEqual(self.m.pop('a'), 1)
        self.assertEqual(self.m.pop('q', default=99), 99)

        with self.assertRaises(KeyError):
            self.e.pop('q')

    def test_popitem(self):
        self.e['a'] = 1
        self.assertEqual(self.e.popitem(), ('a', 1))

    def test_add(self):
        self.e.add('q', 1)
        self.asserte({'q': [1]})

        self.e.add('q', 9)
        self.asserte({'q': [1, 9]})

    def test_get_with_default(self):
        self.assertEqual(self.m.get('a'), 1)

    def test_get_error(self):
        self.assertEqual(self.m.get('q', default=3), 3)

    def test_get_with_type(self):
        self.e['a'] = '1'
        v = self.e.get('a', type=int)
        self.assertEqual(v, 1)

    def test_getlist(self):
        self.assertEqual(self.m.getlist('b'), [2])
        self.assertEqual(self.m.getlist('c'), [3, 4])

        x = MultiDict({'a': ['1', 'a'], 'b': ['2', '3']})
        self.assertEqual(x.getlist('a', type=int), [1])
        self.assertEqual(x.getlist('b', type=int), [2, 3])

        self.assertEqual(self.m.getlist('q'), [])

    def test_setlist(self):
        self.e.setlist('q', [1, 2, 3])
        self.asserte({'q': [1, 2, 3]})

    def test_setlistdefault(self):
        self.e.setlistdefault('q', [1, 2, 3])
        self.asserte({'q': [1, 2, 3]})

        self.assertEqual(self.e.setlistdefault('q'), [1, 2, 3])

    def test_setlistdefault_empty(self):
        self.e.setlistdefault('q')
        self.asserte({'q': []})

    def test_poplist(self):
        self.assertEqual(self.m.poplist('c'), [3, 4])

    def test_popitemlist(self):
        self.e.setlist('q', [1, 2, 3])
        self.assertEqual(self.e.popitemlist(), ('q', [1, 2, 3]))

    def test_copy_module(self):
        c = copy.copy(self.e)
        self.assertTrue(isinstance(c, MultiDict))
        self.assertIsNot(c, self.e)

    def test_iter(self):
        self.assertEqual(sorted(list(iter(self.m))), ['a', 'b', 'c'])

    def test_values(self):
        self.assertEqual(sorted(list(self.m.values())), [1, 2, 3])

    def test_keys(self):
        self.assertEqual(sorted(list(self.m.keys())), ['a', 'b', 'c'])

    def test_items(self):
        i = sorted(list(self.m.items(multi=False)))
        self.assertEqual(i, [('a', 1), ('b', 2), ('c', 3)])

        i = sorted(list(self.m.items(multi=True)))
        self.assertEqual(i, [('a', 1), ('b', 2), ('c', 3), ('c', 4)])

    def test_lists(self):
        l = sorted(list(self.m.lists()))
        self.assertEqual(l, [
            ('a', [1]),
            ('b', [2]),
            ('c', [3, 4]),
        ])

    def test_listvalues(self):
        l = sorted(list(self.m.listvalues()))
        self.assertEqual(l, [
            [1],
            [2],
            [3, 4]
        ])

    def test_proper_iterator(self):
        def assert_iterator(val):
            self.assertTrue(isinstance(val, collections.Iterable))

        def assert_list(val):
            self.assertTrue(isinstance(val, list))

        if PY3:
            assert_func = assert_iterator
        else:
            assert_func = assert_list

        for f in ['items', 'values', 'lists', 'listvalues']:
            # Assert that the bare function matches this Python version's dict
            # behavior
            assert_func(getattr(self.e, f)())

            # Assert that the "iter" + name version is always an iterator.
            assert_iterator(getattr(self.e, "iter" + f)())

    def test_to_dict(self):
        d1 = self.m.to_dict(flat=True)
        for _, v in iteritems(d1):
            self.assertFalse(isinstance(v, list))

        d2 = self.m.to_dict(flat=False)
        for _, v in iteritems(d2):
            self.assertTrue(isinstance(v, list))


class TestCallbackList(unittest.TestCase):
    def setUp(self):
        self.call_count = 0

        class MyList(CallbackList):
            def on_change(this):
                self.call_count += 1

        self.l = MyList()

    def assertl(self, val):
        self.assertEqual(self.l, val)

    @contextlib.contextmanager
    def assert_modified(self, count_or_val):
        self.call_count = 0

        yield

        if count_or_val is True:
            self.assertTrue(self.call_count > 0)
        else:
            self.assertEqual(self.call_count, count_or_val)

    def test_init(self):
        cb_list = CallbackList([1, 2, 3])
        self.assertEqual(list(cb_list), [1, 2, 3])

    def test_setting(self):
        self.l.append(1)

        with self.assert_modified(1):
            self.l[0] = 2

        self.assertl([2])

    def test_getting(self):
        self.l.append(1)

        with self.assert_modified(False):
            self.l[0]

    def test_append(self):
        with self.assert_modified(2):
            self.l.append(1)
            self.l.append(2)

        self.assertl([1, 2])

    def test_count(self):
        self.l = CallbackList([1, 2, 3, 3, 3])

        with self.assert_modified(False):
            self.assertEqual(self.l.count(3), 3)

    def test_extend(self):
        with self.assert_modified(1):
            self.l.extend([4, 5, 6])

        self.assertl([4, 5, 6])

    def test_index(self):
        self.l.extend([4, 5, 6])

        with self.assert_modified(False):
            self.assertEqual(self.l.index(5), 1)

    def test_insert(self):
        with self.assert_modified(3):
            self.l.insert(0, 1)
            self.l.insert(0, 2)
            self.l.insert(0, 3)

        self.assertl([3, 2, 1])

    def test_pop(self):
        self.l.extend([1, 2, 3])

        with self.assert_modified(1):
            self.l.pop()

        self.assertl([1, 2])

    def test_remove(self):
        self.l.extend([1, 2, 3])

        with self.assert_modified(1):
            self.l.remove(3)

        self.assertl([1, 2])

    def test_reverse(self):
        self.l.extend([1, 2, 3])

        with self.assert_modified(1):
            self.l.reverse()

        self.assertl([3, 2, 1])

    def test_sort(self):
        self.l.extend([2, 1, 3])

        with self.assert_modified(1):
            self.l.sort()

        self.assertl([1, 2, 3])

    def test_eq(self):
        self.assertTrue(self.l == [])
        self.assertTrue(CallbackList([1, 2, 3]) == CallbackList([1, 2, 3]))
        self.assertFalse(self.l == 3)


class TestCallbackDict(unittest.TestCase):
    def setUp(self):
        self.call_count = 0

        class MyDict(CallbackDict):
            def on_change(this):
                self.call_count += 1

        self.d = MyDict()

    def assertd(self, val):
        self.assertEqual(self.d, val)

    @contextlib.contextmanager
    def assert_modified(self, count_or_val):
        self.call_count = 0

        yield

        if count_or_val is True:
            self.assertTrue(self.call_count > 0)
        else:
            self.assertEqual(self.call_count, count_or_val)

    def test_init(self):
        d = CallbackDict(foo=1, bar=2)
        self.assertEqual(d, {'foo': 1, 'bar': 2})

    def test_getting(self):
        self.d.update({'foo': 1, 'bar': 2})

        with self.assert_modified(False):
            self.d['foo']

    def test_setting(self):
        with self.assert_modified(1):
            self.d['qq'] = 3

    def test_len(self):
        self.d.update({'foo': 1, 'bar': 2})
        with self.assert_modified(False):
            self.assertEqual(len(self.d), 2)

    def test_clear(self):
        self.d.update({'foo': 1, 'bar': 2})

        with self.assert_modified(1):
            self.d.clear()

    def test_copy(self):
        self.d.update({'foo': 1, 'bar': 2})
        c = self.d.copy()
        self.assertEqual(c, {'foo': 1, 'bar': 2})

    def test_copy_module(self):
        c = copy.copy(self.d)
        self.assertEqual(c, self.d)

    def test_get(self):
        with self.assert_modified(False):
            self.d.get('foo')
            self.d.get('qqq')

    def test_pop(self):
        self.d.update({'foo': 1, 'bar': 2})

        with self.assert_modified(1):
            self.d.pop('foo')

        with self.assert_modified(False):
            self.d.pop('nonexisting', None)

        self.assertd({'bar': 2})

    def test_popitem(self):
        self.d.update({'foo': 1, 'bar': 2})

        with self.assert_modified(1):
            self.d.popitem()

    def test_update(self):
        with self.assert_modified(1):
            self.d.update({'foo': 1, 'bar': 2})

        self.assertd({'foo': 1, 'bar': 2})


class TestCallbackMultiDict(unittest.TestCase):
    def setUp(self):
        self.call_count = 0

        class MyMultiDict(CallbackMultiDict):
            def on_change(this):
                self.call_count += 1

        self.d = MyMultiDict()

    def assertd(self, val):
        self.assertEqual(self.d.to_dict(flat=False), val)

    @contextlib.contextmanager
    def assert_modified(self, count_or_val):
        self.call_count = 0

        yield

        if count_or_val is True:
            self.assertTrue(self.call_count > 0)
        else:
            self.assertEqual(self.call_count, count_or_val)

    def test_getting(self):
        self.d[1] = 2
        with self.assert_modified(0):
            self.d[1]

    def test_setting(self):
        with self.assert_modified(1):
            self.d[1] = 2

    def test_add(self):
        with self.assert_modified(2):
            self.d.add(1, 2)
            self.d.add(1, 3)

        self.assertd({1: [2, 3]})

    def test_delete(self):
        self.d[1] = 2
        with self.assert_modified(1):
            del self.d[1]

        self.assertd({})

    def test_clear(self):
        self.d[1] = 2
        self.d[3] = 4

        with self.assert_modified(1):
            self.d.clear()

        self.assertd({})

    def test_pop(self):
        self.d.add(1, 1)
        self.d.add(1, 2)

        with self.assert_modified(1):
            self.d.pop(1)

    @xfail(reason="on_change() always called")
    def test_pop_not_modified(self):
        with self.assert_modified(0):
            self.d.pop(1, 'default')

    def test_popitem(self):
        self.d[1] = 2

        with self.assert_modified(1):
            self.d.popitem()

    def test_popitemlist(self):
        self.d.add(1, 1)
        self.d.add(1, 2)

        with self.assert_modified(1):
            self.d.popitemlist()

    def test_setdefault(self):
        self.d[1] = 2

        with self.assert_modified(1):
            self.d.setdefault(3, 4)

        self.assertEqual(self.d[1], 2)

    @xfail(reason="on_change() always called")
    def test_setdefault_not_modified(self):
        with self.assert_modified(0):
            self.d.setdefault(1, 5)

        self.assertEqual(self.d[3], 4)

    def test_setlist(self):
        with self.assert_modified(1):
            self.d.setlist(1, [2, 3])

    def test_setlistdefault(self):
        with self.assert_modified(1):
            self.d.setlistdefault(2, [3, 4])

    @xfail(reason="on_change() always called")
    def test_setlistdefault_not_modified(self):
        self.d[1] = 2

        with self.assert_modified(0):
            self.d.setlistdefault(1, [3, 4])

    def test_update(self):
        with self.assert_modified(1):
            self.d.update({1: 2, 3: 4})

        self.assertd({1: [2], 3: [4]})


class TestReturnTranslatingMultiDict(unittest.TestCase):
    def setUp(self):
        self.r = ReturnTranslatingMultiDict({'foo': 1, 'bar': 2, 3: 4})
        self.e = ReturnTranslatingMultiDict()

        def trans(val):
            # print("Translating: %r --> %r" % (val, val + 1))
            return val + 1
        self.r.__rettrans__ = self.e.__rettrans__ = trans

    def assertr(self, val):
        self.assertEqual(self.r.to_dict(flat=False, original=True), val)

    def asserte(self, val):
        self.assertEqual(self.e.to_dict(flat=False, original=True), val)

    def test_init(self):
        self.assertr({'foo': [1], 'bar': [2], 3: [4]})

    def test_getitem(self):
        self.assertEqual(self.r['foo'], 2)
        self.assertEqual(self.r[3], 5)

    def test_setitem(self):
        self.e['foo'] = 10
        self.assertEqual(self.e['foo'], 11)
        self.asserte({'foo': [10]})

    def test_get(self):
        self.assertEqual(self.r.get('foo'), 2)

    def test_pop(self):
        self.assertEqual(self.r.pop('foo'), 2)
        self.assertr({'bar': [2], 3: [4]})

    def test_setdefault(self):
        self.assertEqual(self.r.setdefault('foo', 6), 2)
        self.assertEqual(self.r.setdefault('qqq', 8), 9)

    def test_getlist(self):
        self.r.add('foo', 3)
        self.assertEqual(self.r.getlist('foo'), [2, 4])

    def test_poplist(self):
        self.r.add('foo', 3)
        self.assertEqual(self.r.poplist('foo'), [2, 4])

    def test_setlistdefault(self):
        self.assertEqual(self.e.setlistdefault('qqq', [1, 2, 3]),
                         [2, 3, 4]
                         )
        self.asserte({'qqq': [1, 2, 3]})

    def test_popitem(self):
        self.e.add('foo', 3)
        k, v = self.e.popitem()

        self.assertEqual(k, 'foo')
        self.assertEqual(v, 4)

    def test_popitemlist(self):
        self.e.add('foo', 3)
        k, v = self.e.popitemlist()

        self.assertEqual(k, 'foo')
        self.assertEqual(v, [4])

    def test_items(self):
        i = list((str(k), str(v)) for (k, v) in self.r.items(original=False))
        self.assertEqual(sorted(i), [('3', '5'), ('bar', '3'), ('foo', '2')])

        i = list((str(k), str(v)) for (k, v) in self.r.items(original=True))
        self.assertEqual(sorted(i), [('3', '4'), ('bar', '2'), ('foo', '1')])

    def test_values(self):
        v = list(self.r.values(original=False))
        self.assertEqual(sorted(v), [2, 3, 5])

        v = list(self.r.values(original=True))
        self.assertEqual(sorted(v), [1, 2, 4])

    def test_lists(self):
        l = list(
            (str(k),
             list(str(x) for x in v)
             ) for (k, v) in self.r.lists(original=False)
        )
        self.assertEqual(sorted(l), [
            ('3', ['5']),
            ('bar', ['3']),
            ('foo', ['2']),
        ])

        l = list(
            (str(k),
             list(str(x) for x in v)
             ) for (k, v) in self.r.lists(original=True)
        )
        self.assertEqual(sorted(l), [
            ('3', ['4']),
            ('bar', ['2']),
            ('foo', ['1']),
        ])

    def test_listvalues(self):
        l = list(self.r.listvalues(original=False))
        self.assertEqual(sorted(l), [[2], [3], [5]])

        l = list(self.r.listvalues(original=True))
        self.assertEqual(sorted(l), [[1], [2], [4]])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestImmutableList))
    suite.addTest(unittest.makeSuite(TestImmutableDict))
    suite.addTest(unittest.makeSuite(TestConvertingDict))
    suite.addTest(unittest.makeSuite(TestImmutableConvertingDict))
    suite.addTest(unittest.makeSuite(TestIterMulti))
    suite.addTest(unittest.makeSuite(TestMultiDict))
    suite.addTest(unittest.makeSuite(TestCallbackList))
    suite.addTest(unittest.makeSuite(TestCallbackDict))
    suite.addTest(unittest.makeSuite(TestReturnTranslatingMultiDict))

    return suite
