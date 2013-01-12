from __future__ import with_statement, absolute_import, print_function

import logging
from functools import wraps
from itertools import repeat
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


def list_wrapper(func):
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
        for key, value in _dict_item_iter(mapping):
            if isinstance(value, (tuple, list)):
                for value in value:
                    yield key, value
            else:
                yield key, value

    else:
        for item in mapping:
            yield item


class MultiDict(ConvertingDict):
    def __init__(self, mapping=None):
        # First, handle initializing from other MultiDicts.
        if isinstance(mapping, MultiDict):
            tmp = ((k, l[:]) for k, l in mapping.iterlists())
            super(MultiDict, self).__init__(tmp)

        # Otherwise, if we're given another dictionary:
        elif isinstance(mapping, dict):
            tmp = {}

            for key, value in iteritems(mapping):
                # We convert lists of things to multidict lists.
                if isinstance(value, (list, tuple)):
                    value = list(value)
                else:
                    value = [value]

                tmp[key] = value

            super(MultiDict, self).__init__(tmp)

        # Otherwise, we assume this is some iterable of some sort.
        else:
            tmp = {}
            for key, value in (mapping or ()):
                tmp.setdefault(key, []).append(value)

            super(MultiDict, self).__init__(tmp)

    # Pickle-related functions
    # #############################
    def __getstate__(self):
        return dict(self.lists())

    def __setstate__(self, value):
        super(MultiDict, self).clear()
        super(MultiDict, self).update(value)

    # Dict access
    # #############################
    def __getitem__(self, key):
        return super(MultiDict, self).__getitem__(key)[0]

    def __setitem__(self, key, value):
        super(MultiDict, self).__setitem__(key, [value])

    # Dict methods.
    # #############################
    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        else:
            default = self[key]

        return default

    def update(self, other):
        for key, value in iter_multi_items(other):
            MultiDict.add(self, key, value)

    def pop(self, key, default=missing):
        """
        Pop the first item for a list in this dict.  Afterwords, the key is
        removed from the dict, so additional values for the same key are
        discarded.
        """
        try:
            return super(MultiDict, self).pop(key)[0]
        except KeyError:
            if default is not missing:
                return default

            raise

    def popitem(self):
        """
        Pop an item from the dict.
        """
        item = super(MultiDict, self).popitem()
        return (item[0], item[1][0])

    # Iteration methods.
    # #############################

    if PY3:             # pragma: no cover
        def items(self, multi=False):
            for key, values in super(MultiDict, self).items():
                if multi:
                    for value in values:
                        yield key, value
                else:
                    yield key, values[0]

        def values(self):
            for values in super(MultiDict, self).values():
                yield values[0]

        def lists(self):
            for key, values in super(MultiDict, self).items():
                yield key, list(values)

        def listvalues(self):
            return super(MultiDict, self).values()

        def __iter__(self):
            return iter(super(MultiDict, self).keys())

        # We keep these here despite the fact we're on Python 3, since it
        # gives us a cross-Python way of getting iteration functions.
        iteritems = items
        itervalues = values
        iterlists = lists
        iterlistvalues = listvalues

        # We don't change this behavior, but have this anyway, for the same
        # reasons as mentioned above.
        def iterkeys(self):
            return super(MultiDict, self).keys()

    else:                   # pragma: no cover
        def iteritems(self, multi=False):
            for key, values in super(MultiDict, self).iteritems():
                if multi:
                    for value in values:
                        yield key, value
                else:
                    yield key, values[0]

        def itervalues(self):
            for values in super(MultiDict, self).itervalues():
                yield values[0]

        def iterlists(self):
            for key, values in super(MultiDict, self).iteritems():
                yield key, list(values)

        def iterlistvalues(self):
            return super(MultiDict, self).itervalues()

        def __iter__(self):
            return super(MultiDict, self).iterkeys()

        # Python 2 list versions.
        items = list_wrapper(iteritems)
        values = list_wrapper(itervalues)
        lists = list_wrapper(iterlists)
        listvalues = list_wrapper(iterlistvalues)

    # MultiDict-specific methods.
    # #############################
    def add(self, key, value):
        """
        Add a new value for a key.
        """
        super(MultiDict, self).setdefault(key, []).append(value)

    def getlist(self, key, type=None):
        """
        Return a list of items for a specific key.  If the key is not in this
        dict, then the return value will be an empty list.

        Similar to get(), if the 'type' parameter is given, then all items in
        the returned list will be converted using that callable.
        """
        try:
            ret = super(MultiDict, self).__getitem__(key)
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
        """
        Set the new list of items for a given key.
        """
        super(MultiDict, self).__setitem__(key, list(new_list))

    def setlistdefault(self, key, default_list=None):
        """
        Like 'setdefault', but sets multiple values.
        """
        if key not in self:
            default_list = list(default_list or ())
            super(MultiDict, self).__setitem__(key, default_list)
        else:
            default_list = super(MultiDict, self).__getitem__(key)

        return default_list

    def poplist(self, key):
        """
        Pop the list for a key from this dict.  If the key is not found in
        the dict, an empty list is returned.
        """
        return super(MultiDict, self).pop(key, [])

    def popitemlist(self):
        """
        Pop a list from the dictionary.  Returns a (key, list) tuple.
        """
        return super(MultiDict, self).popitem()

    def __copy__(self):
        return self.copy()

    def __repr__(self):
        return "%s(%r)" % (
            self.__class__.__name__,
            list(self.items(multi=True))
        )
