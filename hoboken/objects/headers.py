from __future__ import with_statement, absolute_import, print_function
from collections import MutableMapping
from hoboken.six import PY3, iterkeys, iteritems
from hoboken.objects.datastructures import MultiDict


class WSGIHeaders(MutableMapping):
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


class ConvertingMixin(object):
    def __init__(self, *args, **kwargs):
        super(ConvertingMixin, self).__init__(*args, **kwargs)

    def __setitem__(self, name, value):
        if PY3:
            if isinstance(name, bytes):
                name = name.decode('latin-1')
            if isinstance(value, bytes):
                value = value.decode('latin-1')

        return super(ConvertingMixin, self).__setitem__(name, value)

    def __getitem__(self, name):
        val = super(ConvertingMixin, self).__getitem__(name)
        if PY3 and isinstance(val, str):
            val = val.encode('latin-1')
        return val


class WSGIResponseHeaders(ConvertingMixin, MultiDict):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseHeaders, self).__init__(*args, **kwargs)
