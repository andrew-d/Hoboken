from __future__ import with_statement, absolute_import, print_function

__all__ = ['_not_given', '_environ_prop', '_environ_converter', '_int_parser',
           '_int_serializer', 'ImmutableList',
           ]

class _NotGiven(object):
    def __repr__(self):
        return "<not given>"

_not_given = _NotGiven()


def _environ_prop(key, default=_not_given):
    if default is _not_given:
        def getter(self):
            return self.environ[key]
        def setter(self, value):
            self.environ[key] = value
        deleter = None
    else:
        def getter(self):
            return self.environ.get(key, default)
        def setter(self, value):
            if value is None:
                self.environ.pop(key, None)
            else:
                self.environ[key] = value
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


def is_immutable(self):
    raise TypeError('{0!r} objects are immutable'.format(self.__class__.__name__))


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
