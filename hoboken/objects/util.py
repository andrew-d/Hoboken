from __future__ import with_statement, absolute_import, print_function
from io import RawIOBase

from hoboken.six import advance_iterator, callable

__all__ = ['missing', '_environ_prop', '_environ_converter', '_int_parser',
           '_int_serializer', 'cached_property', 'iter_close',
           'BytesIteratorFile'
           ]

class MissingObject(object):
    def __repr__(self):
        return "<missing>"

    def __str__(self):
        raise AttributeError("__str__ not supported!")

missing = MissingObject()


def _environ_prop(key, default=missing, doc=''):
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
    return property(getter, setter, deleter, doc=doc)


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
    if value is None or value == b'':
        return None
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

