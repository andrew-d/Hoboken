from __future__ import with_statement, absolute_import, print_function

import logging
from functools import wraps
from itertools import repeat
from collections import MutableMapping, MutableSequence
from hoboken.six import iteritems, PY3
from hoboken.objects.util import missing

# Note: much of the code in this module is inspired by code from Werkzeug
# (https://github.com/mitsuhiko/werkzeug/) or Brownie
# (https://github.com/DasIch/brownie).  Their associated license files can be
# found in the LICENSE_werkzeug.txt and LICENSE_brownie.rst files in the same
# directory as this file.


logger = logging.getLogger(__name__)


def is_immutable(self):
    logger.error("Attempted to mutate an immutable structure: %r", self)
    raise TypeError(
        '{0!r} objects are immutable'.format(self.__class__.__name__)
    )


class ImmutableListMixin(object):
    """
    This mixin makes a list immutable.
    """

    _hash_cache = None

    def __hash__(self):
        if self._hash_cache is not None:
            return self._hash_cache
        rv = self._hash_cache = hash(tuple(self))
        return rv

    def __reduce_ex__(self, protocol):
        return type(self), (list(self),)

    def __delitem__(self, key):
        is_immutable(self)

    # Marked as 'no cover' since it's not used on Py3, apparently.
    def __delslice__(self, i, j):           # pragma: no cover
        is_immutable(self)

    def __iadd__(self, other):
        is_immutable(self)
    __imul__ = __iadd__

    def __setitem__(self, key, value):
        is_immutable(self)

    # Marked as 'no cover' since it's not used on Py3, apparently.
    def __setslice__(self, i, j, value):    # pragma: no cover
        is_immutable(self)

    def append(self, item):
        is_immutable(self)
    remove = append

    def extend(self, iterable):
        is_immutable(self)

    def insert(self, pos, value):
        is_immutable(self)

    def pop(self, index=-1):
        is_immutable(self)

    def reverse(self):
        is_immutable(self)

    def sort(self, cmp=None, key=None, reverse=None):
        is_immutable(self)


class ImmutableList(ImmutableListMixin, list):
    pass


class ImmutableDictMixin(object):
    """
    This mixin makes a dict immutable.
    """
    _hash_cache = None

    @classmethod
    def fromkeys(cls, keys, value=None):
        instance = super(cls, cls).__new__(cls)
        instance.__init__(zip(keys, repeat(value)))
        return instance

    def __reduce_ex__(self, protocol):
        return type(self), (dict(self),)

    def _iter_hashitems(self):
        return iteritems(self)

    def __hash__(self):
        if self._hash_cache is not None:
            return self._hash_cache

        # NOTE: We use _iter_hashitems() here, so that when we subclass this
        # class, we can customize what we iterate over.
        ret = self._hash_cache = hash(frozenset(self._iter_hashitems()))
        return ret

    def setdefault(self, key, default=None):
        is_immutable(self)

    def update(self, *args, **kwargs):
        is_immutable(self)

    def pop(self, key, default=None):
        is_immutable(self)

    def popitem(self):
        is_immutable(self)

    def __setitem__(self, key, value):
        is_immutable(self)

    def __delitem__(self, key):
        is_immutable(self)

    def clear(self):
        is_immutable(self)


class ImmutableDict(ImmutableDictMixin, dict):
    """
    An immutable dict.
    """
    def copy(self):
        """
        When copies are made, we use the built-in dict() class.
        """
        return dict(self)

    def __copy__(self):
        """
        This method makes the standard library's copy() function a no-op,
        just like it is for, e.g., tuples.
        """
        return self


class ConvertingDict(dict):
    """
    This class acts like an ordinary dict() in every way, except that the
    get() function can perform type conversions.
    """
    def get(self, key, default=None, type=None):
        try:
            ret = self[key]
            if type is not None:
                ret = type(ret)
        except (KeyError, ValueError):
            ret = default

        return ret


class ImmutableConvertingDict(ImmutableDictMixin, ConvertingDict):
    """
    An immutable version of a ConvertingDict.
    """
    def copy(self):
        return ConvertingDict(self)

    def __copy__(self):
        return self


def list_wrapper(func):     # pragma: no cover
    @wraps(func)
    def wrapper_func(*args, **kwargs):
        return list(func(*args, **kwargs))

    return wrapper_func


def iter_multi_items(mapping):
    """
    Iterate over the items in a mapping, properly handling more complex data
    structures.
    """
    if isinstance(mapping, MultiDict):
        # Note: we don't unpack (key, value) from item.
        for item in mapping.iteritems(multi=True):
            yield item

    elif isinstance(mapping, dict):
        for key, value in iteritems(mapping):
            if isinstance(value, (tuple, list)):
                for value in value:
                    yield key, value
            else:
                yield key, value

    else:
        for item in mapping:
            yield item


class MultiDict(MutableMapping):
    def __init__(self, mapping=None):
        self.__d = {}
        _kt = self.__keytrans__
        _vt = self.__valtrans__

        # First, handle initializing from other MultiDicts.
        if isinstance(mapping, MultiDict):
            tmp = (
                (
                    _kt(k),
                    list(_vt(x) for x in l)
                ) for k, l in mapping.iterlists()
            )
            self.__d = dict(tmp)

        # Otherwise, if we're given another dictionary:
        elif isinstance(mapping, dict):
            tmp = {}

            for key, value in iteritems(mapping):
                # We convert lists of things to multidict lists.
                if isinstance(value, (list, tuple)):
                    value = list(_vt(x) for x in value)
                else:
                    value = [_vt(value)]

                tmp[_kt(key)] = value

            self.__d = tmp

        # Otherwise, we assume this is some iterable of some sort.
        else:
            tmp = {}
            for key, value in (mapping or ()):
                tmp.setdefault(_kt(key), []).append(_vt(value))

            self.__d = tmp

    @classmethod
    def fromkeys(cls, keys, value=None):
        instance = cls.__new__(cls)
        instance.__init__(zip(keys, repeat(value)))
        return instance

    # Function hooks.
    # --------------------------------------------------
    def __keytrans__(self, key):
        """
        Translate a key before it's used to index the MultiDict.
        """
        return key

    def __valtrans__(self, val):
        """
        Translate a value before being written to the dictionary.
        """
        return val

    # MutableMapping functions that must be implemented.
    # --------------------------------------------------
    def __getitem__(self, key):
        try:
            return self.__d[self.__keytrans__(key)][0]
        except KeyError:
            raise KeyError(key)

    def __setitem__(self, key, val):
        self.__d[self.__keytrans__(key)] = [self.__valtrans__(val)]

    def __delitem__(self, key):
        del self.__d[self.__keytrans__(key)]

    def __len__(self):
        return len(self.__d)

    def copy(self):
        return self.__class__(self)

    def __copy__(self):
        return self.copy()

    # Dict functions.
    # --------------------------------------------------
    def get(self, key, default=None, type=None):
        try:
            ret = self[key]
            if type is not None:
                ret = type(ret)
        except (KeyError, ValueError):
            ret = default

        return ret

    if not PY3:     # pragma: no cover
        def has_key(self, key):
            return key in self

    def update(self, other):
        for key, value in iter_multi_items(other):
            self.add(key, value)

    # Pickle-related stuff
    # --------------------------------------------------
    def __getstate__(self):
        return dict(self.lists())

    def __setstate__(self, value):
        # Since Pickle doesn't call our __init__ function, initialize ourself.
        self.__d = {}

        # Set the values on the dict.
        self.clear()
        self.update(value)

    # MultiDict-specific methods.
    # --------------------------------------------------
    def add(self, key, value):
        key = self.__keytrans__(key)
        val = self.__valtrans__(value)
        self.__d.setdefault(key, []).append(val)

    def getlist(self, key, type=None):
        key = self.__keytrans__(key)

        try:
            ret = self.__d[key]
        except KeyError:
            return []

        if type is None:
            return list(ret)

        result = []
        for x in ret:
            try:
                result.append(type(x))
            except ValueError:
                pass

        return result

    def setlist(self, key, new_list):
        key = self.__keytrans__(key)
        self.__d[key] = list(self.__valtrans__(x) for x in new_list)

    def setlistdefault(self, key, default_list=None):
        key = self.__keytrans__(key)

        if key not in self:
            if default_list is not None:
                default_list = list(
                    self.__valtrans__(x) for x in default_list
                )
            else:
                default_list = ()

            self.__d[key] = default_list
        else:
            default_list = self.__d[key]

        return default_list

    def poplist(self, key):
        key = self.__keytrans__(key)
        return self.__d.pop(key, [])

    def popitemlist(self):
        return self.__d.popitem()

    def to_dict(self, flat=True, **kwargs):
        if flat:
            return dict(self.iteritems(**kwargs))
        return dict(self.lists(**kwargs))

    # Iteration methods.
    # --------------------------------------------------
    if PY3:             # pragma: no cover
        def items(self, multi=False):
            for key, values in self.__d.items():
                if multi:
                    for value in values:
                        yield key, value
                else:
                    yield key, values[0]

        def values(self):
            for values in self.__d.values():
                yield values[0]

        def lists(self):
            for key, values in self.__d.items():
                yield key, list(values)

        def listvalues(self):
            return self.__d.values()

        def __iter__(self):
            return iter(self.__d.keys())

        # We keep these here despite the fact we're on Python 3, since it
        # gives us a cross-Python way of getting iteration functions.
        iteritems = items
        itervalues = values
        iterlists = lists
        iterlistvalues = listvalues

        # We don't change this behavior, but have this anyway, for the same
        # reasons as mentioned above.
        def iterkeys(self):
            return self.__d.keys()

    else:                   # pragma: no cover
        def iteritems(self, multi=False):
            for key, values in self.__d.iteritems():
                if multi:
                    for value in values:
                        yield key, value
                else:
                    yield key, values[0]

        def itervalues(self):
            for values in self.__d.itervalues():
                yield values[0]

        def iterlists(self):
            for key, values in self.__d.iteritems():
                yield key, list(values)

        def iterlistvalues(self):
            return self.__d.itervalues()

        def __iter__(self):
            return self.__d.iterkeys()

        # Python 2 list versions.
        items = list_wrapper(iteritems)
        values = list_wrapper(itervalues)
        lists = list_wrapper(iterlists)
        listvalues = list_wrapper(iterlistvalues)

    def __repr__(self):
        return "%s(%r)" % (
            self.__class__.__name__,
            list(self.items(multi=True))
        )


class CallbackList(MutableSequence):
    def __init__(self, iterable=None):
        if iterable is not None:
            self.__list = list(iterable)
        else:
            self.__list = list()

    # This is our callback function for list modifications.  Override it!
    def on_change(self):        # pragma: no cover
        pass

    # The following methods are methods that need to be provided for a
    # MutableSequence to be instantiated.
    def __getitem__(self, idx):
        return self.__list[idx]

    def __setitem__(self, idx, val):
        self.__list[idx] = val
        self.on_change()

    def __delitem__(self, idx):
        del self.__list[idx]
        self.on_change()

    def __len__(self):
        return len(self.__list)

    def insert(self, idx, val):
        self.__list.insert(idx, val)
        self.on_change()

    # MutableSequence doesn't provide the sort() function, so we do.
    def sort(self, *args, **kwargs):
        self.__list.sort(*args, **kwargs)
        self.on_change()

    # Note that we provide concrete implementations for these next two methods
    # since otherwise the on_change() function is called multiple times.
    def extend(self, *args, **kwargs):
        self.__list.extend(*args, **kwargs)
        self.on_change()

    def reverse(self, *args, **kwargs):
        self.__list.reverse(*args, **kwargs)
        self.on_change()

    # We override the __eq__ method to support comparing with regular lists.
    # Otherwise, it seems like they won't compare properly.
    def __eq__(self, other):
        if isinstance(other, list):
            return list(self) == other
        elif isinstance(other, CallbackList):
            return self.__list == other.__list
        else:
            return NotImplemented

    # Proxy the __repr__ to the underlying list.
    def __repr__(self):
        return repr(self.__list)


class CallbackDict(MutableMapping):
    def __init__(self, *args, **kwargs):
        self.__dict = dict(*args, **kwargs)

    # This is our callback function for dict modifications.  Override it!
    def on_change(self):        # pragma: no cover
        pass

    # The following methods are methods that need to be provided for a
    # MutableMapping to be instantiated.
    def __getitem__(self, key):
        return self.__dict[key]

    def __setitem__(self, key, val):
        self.__dict[key] = val
        self.on_change()

    def __delitem__(self, key):
        del self.__dict[key]
        self.on_change()

    def __len__(self):
        return len(self.__dict)

    def __iter__(self):
        return iter(self.__dict)

    # Note that we provide concrete implementations for these next two methods
    # since otherwise the on_change() function is called multiple times.
    def clear(self):
        self.__dict.clear()
        self.on_change()

    def update(self, *args, **kwargs):
        self.__dict.update(*args, **kwargs)
        self.on_change()

    # MutableMapping doesn't provide a copy() function, so we do.
    def copy(self):
        return self.__class__(self)

    def __copy__(self):
        return self.copy()

    # Proxy the __repr__ to the underlying dict.
    def __repr__(self):
        return repr(self.__dict)


# Wrap every function in a wrapper that will call the '__rettrans__' function
# on the output.  This is kinda confusing, so here's a breakdown:
#  - When a function is called on this class, it actually calls our wrapper
#    function.
#  - The wrapper function calls the original function, and gets the return
#    value.
#  - The wrapper then calls the __rettrans__ function with the return value to
#    obtain a (possibly) new return value.
#  - The wrapper function then returns the newly-translated return value.
def _make_list_wrapper(func):
    @wraps(func)
    def new_function(self, *args, **kwargs):
        ret = func(self, *args, **kwargs)
        return list(self.__rettrans__(x) for x in ret)

    return new_function


class ReturnTranslatingMultiDict(MultiDict):
    # Dummy translating func.
    def __rettrans__(self, val):        # pragma: no cover
        return val

    # This returns a single value, so we just wrap it as-is.
    def __getitem__(self, key):
        return self.__rettrans__(
            super(ReturnTranslatingMultiDict, self).__getitem__(key)
        )

    # We need to provide a concrete implementation of setdefault, since we
    # only want to translate the return value if we don't read from the dict
    # (since the read will call __getitem__, which then already translates).
    def setdefault(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            self[key] = default

        return self.__rettrans__(default)

    # These functions return a list of values, so we need to wrap them in a
    # variant that handles this.
    getlist = _make_list_wrapper(MultiDict.getlist)
    poplist = _make_list_wrapper(MultiDict.poplist)
    setlistdefault = _make_list_wrapper(MultiDict.setlistdefault)

    # This is special, in that it returns a (key, value) tuple.  We need to
    # deal with this manually.
    def popitemlist(self):
        (k, v) = super(ReturnTranslatingMultiDict, self).popitemlist()
        return (k, list(self.__rettrans__(x) for x in v))

    # Iteration methods
    def iteritems(self, **kwargs):
        if kwargs.pop('original', False):
            return super(ReturnTranslatingMultiDict, self).iteritems(**kwargs)

        return (
            (k, self.__rettrans__(v)) for (k, v) in
            super(ReturnTranslatingMultiDict, self).iteritems(**kwargs)
        )

    def itervalues(self, **kwargs):
        if kwargs.pop('original', False):
            return super(ReturnTranslatingMultiDict,
                         self).itervalues(**kwargs)

        return (self.__rettrans__(x) for x in
                super(ReturnTranslatingMultiDict, self).itervalues())

    def iterlists(self, **kwargs):
        if kwargs.pop('original', False):
            return super(ReturnTranslatingMultiDict, self).iterlists(**kwargs)

        return (
            (k, list(self.__rettrans__(x) for x in v)) for (k, v)
            in super(ReturnTranslatingMultiDict, self).iterlists()
        )

    def iterlistvalues(self, **kwargs):
        if kwargs.pop('original', False):
            return super(ReturnTranslatingMultiDict,
                         self).iterlistvalues(**kwargs)

        return list(
            list(self.__rettrans__(l) for l in x) for x in
            super(ReturnTranslatingMultiDict, self).iterlistvalues()
        )

    # Remember, iteration is different on Python 2/3.
    if PY3:         # pragma: no cover
        lists = iterlists
        items = iteritems
        values = itervalues
        listvalues = iterlistvalues

    else:           # pragma: no cover
        # Python 2 list versions.
        items = list_wrapper(iteritems)
        values = list_wrapper(itervalues)
        lists = list_wrapper(iterlists)
        listvalues = list_wrapper(iterlistvalues)
