from __future__ import with_statement, absolute_import, print_function
import re
from collections import MutableMapping
from .base import BaseRequest
from .util import *
from ..six import *

try:
    import urllib.parse
    _quote = urllib.parse.quote
except ImportError:
    import urllib
    _quote = urllib.quote


# TODO: replace this with one that works on bytes
def quote(value):
    quoted = _quote(value)
    if isinstance(quoted, text_type):
        quoted = quoted.encode('latin-1')
    return quoted


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


class WSGIBaseRequest(BaseRequest):
    def __init__(self, environ, charset='utf-8'):
        super(WSGIBaseRequest, self).__init__()
        if type(environ) is not dict:
            raise ValueError("The WSGI environ must be a dict, not a {0!r}".format(type(environ)))

        self.environ = environ
        self.charset = charset

    if PY3:
        def _to_wsgi_str(self, value):
            if isinstance(value, bytes):
                value = value.decode('latin-1')
            elif isinstance(value, str):
                # Encode and then decode to verify that this string only contains
                # valid codepoints.
                value = value.encode('latin-1').decode('latin-1')

            return value

        def _from_wsgi_str(self, value):
            # By default, we return all values as bytestrings.
            if isinstance(value, str):
                value = value.encode('latin-1')
            return value
    else:
        def _to_wsgi_str(self, value):
            if isinstance(value, unicode):
                value = value.encode('latin-1')
            return value

        def _from_wsgi_str(self, value):
            if isinstance(value, unicode):
                value = value.encode('latin-1')
            return value

    method = _environ_prop('REQUEST_METHOD', b'GET')
    scheme = _environ_prop('wsgi.url_scheme')
    script_name = _environ_prop('SCRIPT_NAME', b'')
    path_info = _environ_prop('PATH_INFO', b'')
    query_string = _environ_prop('QUERY_STRING', b'')
    http_version = _environ_prop('SERVER_PROTOCOL')

    content_length = _environ_converter(_environ_prop('CONTENT_LENGTH', None),
                                        _int_parser, _int_serializer)
    server_port = _environ_converter(_environ_prop('SERVER_PORT'),
                                     _int_parser, _int_serializer)

    remote_addr = _environ_prop('REMOTE_ADDR', None)
    remote_user = _environ_prop('REMOTE_USER', None)
    server_name = _environ_prop('SERVER_NAME')

    _headers = None
    def _headers_getter(self):
        if self._headers is None:
            self._headers = WSGIHeaders(self.environ)
        return self._headers

    def _headers_setter(self, value):
        self.headers.clear()
        self.headers.update(value)

    headers = property(_headers_getter, _headers_setter)

    input_stream = _environ_prop('wsgi.input')


class WSGIRequest(WSGIBaseRequest):
    _STRIP_PORT = re.compile(br":\d+\Z")

    def __init__(self, *args, **kwargs):
        super(WSGIRequest, self).__init__(*args, **kwargs)

    @WSGIBaseRequest.path_info.getter
    def path_info(self):
        """
        An override of path_info's getter that ensures we always have a
        leading slash.
        """
        val = super(WSGIRequest, self).path_info
        return b'/' + val.lstrip(b'/')

    @property
    def host_with_port(self):
        if self.headers.get(b'Host'):
            return self.headers[b'Host']
        else:
            host = self.server_name

            if self.scheme == b'https':
                if self.server_port != 443:
                   host += b':' + str(self.server_port).encode('latin-1')
            else:
                if self.server_port != 80:
                   host += b':' + str(self.server_port).encode('latin-1')

        return host

    @property
    def host(self):
        return self._STRIP_PORT.sub(b'', self.host_with_port)

    @property
    def port(self):
        spl = self.host_with_port.split(b':')
        if len(spl) > 1:
            return int(spl[1])

        if self.headers.get(b'X-Forwarded-Port'):
            return int(self.headers[b'X-Forwarded-Port'])

        if self.scheme == b'https':
            return 443

        if b'X-Forwarded-Host' in self.headers:
            return 80

        return self.server_port

    @property
    def path(self):
        return self.script_name + self.path_info

    @property
    def full_path(self):
        path = self.path
        if len(self.query_string) > 0:
            path += b'?' + self.query_string
        return path

    @property
    def url(self):
        """ The full URL of the request."""
        # This code adapted from PEP 3333, thanks to Ian Bicking.
        url = self.scheme + b'://'

        url += self.host_with_port

        path = '/' + self.path.lstrip(b'/')

        url += quote(path)
        if len(self.query_string) > 0:
            url += b'?' + self.query_string

        return url

    @property
    def is_secure(self):
        return self.scheme == b'https'

    def __str__(self):
        parts = [self.method + b' ' +
                 self.full_path + b' ' +
                 self.http_version]

        for k, v in sorted(self.headers.items()):
            parts.append(k + b': ' + v)

        return b"\r\n".join(parts)


from .mixins.accept import WSGIAcceptMixin
from .mixins.cache import WSGIRequestCacheMixin

class WSGIFullRequest(WSGIRequest, WSGIAcceptMixin, WSGIRequestCacheMixin):
    pass
