from __future__ import with_statement, absolute_import, print_function
from functools import wraps
from collections import MutableMapping
from hoboken.six import binary_type, PY3, iterkeys, iteritems, text_type
from hoboken.objects.datastructures import MultiDict


class EnvironHeaders(MutableMapping):
    """
    This class is a mapping for a set of HTTP headers constructed from a WSGI
    environ.  Since, in a request, all headers with the same name will be
    collapsed into a single header, this class is simpler and doesn't need to
    handle the multiple header case.
    """
    def __init__(self, environ):
        self.environ = environ

    def _realname(self, name):
        if PY3 and isinstance(name, bytes):
            name = name.decode('latin-1')
        name = name.upper()
        return 'HTTP_' + name.replace('-', '_')

    def __getitem__(self, name):
        val = self.environ[self._realname(name)]
        if PY3 and isinstance(val, str):
            val = val.encode('latin-1')
        return val

    def __setitem__(self, name, value):
        if PY3 and isinstance(value, bytes):
            value = value.decode('latin-1')
        self.environ[self._realname(name)] = value

    def __delitem__(self, name):
        del self.environ[self._realname(name)]

    def __contains__(self, name):
        return self._realname(name) in self.environ

    def __len__(self):
        return len(self.keys())

    def keys(self):
        return list(iter(self))

    def __iter__(self):
        for key in iterkeys(self.environ):
            if isinstance(key, str) and key.startswith('HTTP_'):
                yield key[5:].replace('_', '-').title()

    def to_list(self):
        return list(iteritems(self))


def _to_wsgi(val):  # pragma: no cover
    if PY3:
        if isinstance(val, bytes):
            val = val.decode('latin-1')
        elif isinstance(val, str):
            val = val.encode('latin-1').decode('latin-1')
    else:
        if isinstance(val, unicode):
            val = val.encode('latin-1')

    return val


class ResponseHeaders(MultiDict):
    """
    Unlike in a request, a response can have multiple headers with the same
    name.  Thus, this class is a subclass of a MultiDict, with the various
    accessor functions overridden to handle dealing with the bytes/unicode
    difference on Python 3.
    """
    def __init__(self, *args, **kwargs):
        super(ResponseHeaders, self).__init__(*args, **kwargs)

    def __keytrans__(self, key):
        return _to_wsgi(key)

    def __valtrans__(self, val):
        return _to_wsgi(val)

