from __future__ import with_statement, absolute_import, print_function

__all__ = ['_not_given', '_environ_prop', '_environ_converter', '_int_parser',
           '_int_serializer'
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

