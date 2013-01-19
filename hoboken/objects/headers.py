from __future__ import with_statement, absolute_import, print_function

import re
from functools import wraps
from collections import MutableMapping
from hoboken.six import binary_type, PY3, iterkeys, iteritems, text_type
from hoboken.objects.datastructures import list_wrapper


INVALID_HEADER_NAME_RE = re.compile(r'[\x00-\x1F\x7F \:]')
INVALID_HEADER_VAL_RE = re.compile(r'[\r\n]')


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


class ResponseHeaders(MutableMapping):
    def __init__(self, defaults=None):
        self.__l = []

        if defaults is not None:
            if isinstance(defaults, ResponseHeaders):
                self.__l.extend(defaults)
            else:
                self.extend(defaults)

    # Encoding functions
    # --------------------------------------------------
    def _normalize_key(self, key):
        """
        This function will normalize a key by converting to the appropriate
        encoding and to title case.
        """
        if PY3 and isinstance(key, bytes):
            key = key.decode('latin-1')

        # Search for any invalid characters in the header name.  As per RFC
        # 822, a header may contain "any ASCII value, excluding CTLs, SPACE
        # and ':'".
        m = INVALID_HEADER_NAME_RE.search(key)
        if m:
            raise ValueError("Found invalid character %r in the header name "
                             "at position %d.  This is a potential security "
                             "vulnerability, and is not allowed." % (
                                 m.group(0),
                                 m.start(0),
                             ))

        return key.title()

    def _value_encode(self, val):
        """
        This function will encode a value.  It's used when this mapping is
        being written to.  It also performs checks to ensure that we're not
        including any invalid bytes in the header.
        """
        if PY3 and isinstance(val, bytes):
            val = val.decode('latin-1')

        # This should be a regular string now.  We now search for any invalid
        # characters in the header value (just newlines, for now).
        m = INVALID_HEADER_VAL_RE.search(val)
        if m:
            raise ValueError("Found invalid character %r in the header at "
                             "position %d.  This is a potential security "
                             "vulnerability, and is not allowed." % (
                                 m.group(0),
                                 m.start(0),
                             ))

        return val

    def _value_decode(self, val):
        """
        This function will force a value to a bytestring.  This is used when
        we're reading from this mapping.
        """
        if PY3 and isinstance(val, str):
            val = val.encode('latin-1')

        return val

    # MutableMapping functions that must be defined
    # --------------------------------------------------
    def __getitem__(self, key):
        # Normalize the key name.
        norm_key = self._normalize_key(key)

        for (name, val) in self.__l:
            if name == norm_key:
                return self._value_decode(val)

        raise KeyError(key)

    def __setitem__(self, key, val):
        norm_key = self._normalize_key(key)
        norm_val = self._value_encode(val)

        # Remove existing values (without erroring).
        self._remove(norm_key)

        # Add the new header.
        self.__l.append((norm_key, norm_val))

    def __delitem__(self, key):
        norm_key = self._normalize_key(key)
        if not self._remove(norm_key):
            raise KeyError(key)

    def __len__(self):
        return len(self.__l)

    def __iter__(self):
        return iter(self.__l)

    # Other dict functions
    # --------------------------------------------------
    def __contains__(self, key):
        norm_key = self._normalize_key(key)

        for (name, _) in self.__l:
            if name == norm_key:
                return True

        return False

    def clear(self):
        del self.__l[:]

    def copy(self):
        return self.__class__(self)

    def __copy__(self):
        return self.copy()

    def __str__(self):
        """
        Format the headers such that they can be transmitted over HTTP.
        """
        vals = []
        for (k, v) in self.__l:
            vals.append("%s: %s" % (k, v))

        # Add trailing newlines after headers.
        vals.append('\r\n')

        return '\r\n'.join(vals)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.__l)

    # Iteration
    # --------------------------------------------------
    def iteritems(self):
        for (k, v) in self.__l:
            yield (k, v)

    def iterkeys(self):
        for (k, _) in self.__l:
            yield k

    def itervalues(self):
        for (_, v) in self.__l:
            yield v

    if PY3:     # pragma: no cover
        items = iteritems
        keys = iterkeys
        values = itervalues
    else:       # pragma: no cover
        items = list_wrapper(iteritems)
        keys = list_wrapper(iterkeys)
        values = list_wrapper(itervalues)

    # Functions for multiple headers
    # --------------------------------------------------
    def add(self, key, val):
        """
        Add a new header value to our list without removing existing values
        for this header.
        """
        norm_key = self._normalize_key(key)
        norm_val = self._value_encode(val)

        self.__l.append((norm_key, norm_val))

    def get_all(self, key):
        norm_key = self._normalize_key(key)
        return list(filter(lambda v: v[0] == norm_key, self.__l))

    def extend(self, it):
        if isinstance(it, dict):
            for key, val in iteritems(it):
                if isinstance(val, (tuple, list)):
                    for v in val:
                        self.add(key, v)
                else:
                    self.add(key, val)
        else:
            for key, val in it:
                self.add(key, val)

    def remove(self, key):
        """
        Remove a value without erroring if it doesn't exist.  Returns whether
        any elements were removed.
        """
        return self._remove(self._normalize_key(key))

    # Internal functions
    # --------------------------------------------------
    def _remove(self, norm_key):
        lst = self.__l
        found = False

        # Iterate backwards over the array (since when we remove elements, the
        # list is shifted, so we'd have to do funny stuff with the index if we
        # iterate forwards.
        for i in range(len(lst) - 1, -1, -1):
            if lst[i][0] == norm_key:
                del lst[i]
                found = True

        # Return whether we found anything.
        return found
