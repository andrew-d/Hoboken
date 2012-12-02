from __future__ import with_statement, absolute_import, print_function
from io import RawIOBase

from hoboken.six import advance_iterator, callable

__all__ = ['missing', '_environ_prop', '_environ_converter', '_int_parser',
           '_int_serializer', 'cached_property', 'ImmutableList', 'iter_close',
           'BytesIteratorFile'
           ]

class MissingObject(object):
    def __repr__(self):
        return "<missing>"

    def __str__(self):
        raise AttributeError("__str__ not supported!")

missing = MissingObject()


def _environ_prop(key, default=missing):
    if default is missing:
        def getter(self):
            return self._from_wsgi_str(self.environ[key])
        def setter(self, value):
            self.environ[key] = self._to_wsgi_str(value)
        deleter = None
    else:
        def getter(self):
            val = self.environ.get(key, default)
            return self._from_wsgi_str(val)
        def setter(self, value):
            if value is None:
                self.environ.pop(key, None)
            else:
                self.environ[key] = self._to_wsgi_str(value)
        def deleter(self):
            del self.environ[key]

    # TODO: set the docstring properly.
    return property(getter, setter, deleter, doc='')


def _environ_converter(prop, parser, serializer):
    pgetter = prop.fget
    psetter = prop.fset

    def getter(self):
        return parser(pgetter(self))
    def setter(self, value):
        if value is not None:
            value = serializer(value)
        psetter(self, value)
    return property(getter, setter, prop.fdel, prop.__doc__ or '')


def _int_parser(value):
    return int(value)

_int_serializer = str


class cached_property(object):
    def __init__(self, func):
        self.func = func
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__module__ = func.__module__

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        value = obj.__dict__.get(self.__name__, missing)
        if value is missing:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value


def is_immutable(self):
    raise TypeError(
        '{0!r} objects are immutable'.format(self.__class__.__name__)
    )


class ImmutableListMixin(object):
    """
    This mixin makes a list immutable.  Code inspired by some code from
    Werkzeug.
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

    def __delslice__(self, i, j):
        is_immutable(self)

    def __iadd__(self, other):
        is_immutable(self)
    __imul__ = __iadd__

    def __setitem__(self, key, value):
        is_immutable(self)

    def __setslice__(self, i, j, value):
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


def iter_close(iter):
    if hasattr(iter, 'close') and callable(iter.close):
        iter.close()


class BytesIteratorFile(RawIOBase):
    def __init__(self, i):
        self.__iter = iter(i)
        self.__cache = b''
        self.eof = False

    def readall(self):
        ret = b''.join(self.__iter)
        return self.__cache + ret

    def read(self, num=-1):
        if self.eof:
            return b''
        if num == -1:
            return self.readall()

        # Try getting our cache first.
        chunks = [self.__cache]
        total_len = len(self.__cache)

        try:
            while total_len < num:
                next_chunk = advance_iterator(self.__iter)
                chunks.append(next_chunk)
                total_len += len(next_chunk)
        except StopIteration:
            self.eof = True

        # Join together.
        bstr = b''.join(chunks)

        # Trim to required length.
        if len(bstr) > num:
            bstr, cache = bstr[:num], bstr[num:]
        else:
            cache = b''

        # Reset cache, return value.
        self.__cache = cache
        return bstr

