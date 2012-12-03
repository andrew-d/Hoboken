from __future__ import with_statement, absolute_import, print_function
import re

from hoboken.objects.base import BaseRequest
from hoboken.objects.util import *
from hoboken.objects.http import quote, unquote
from hoboken.objects.headers import WSGIHeaders
from hoboken.six import *
from hoboken.objects.oproperty import oproperty, property_overriding



class WSGIBaseRequest(BaseRequest):
    def __init__(self, environ, charset='utf-8'):
        super(WSGIBaseRequest, self).__init__()
        if type(environ) is not dict:
            raise ValueError(
                "The WSGI environ must be a dict, not a {0!r}".format(
                    type(environ)
                )
            )

        self.environ = environ
        self.charset = charset

    if PY3:             # pragma: no cover
        def _to_wsgi_str(self, value):
            if isinstance(value, bytes):
                value = value.decode('latin-1')
            elif isinstance(value, str):
                # Encode and then decode to verify that this string only
                # contains valid codepoints.
                value = value.encode('latin-1').decode('latin-1')

            return value

        def _from_wsgi_str(self, value):
            # By default, we return all values as bytestrings.
            if isinstance(value, str):
                value = value.encode('latin-1')
            return value
    else:               # pragma: no cover
        def _to_wsgi_str(self, value):
            if isinstance(value, unicode):
                value = value.encode('latin-1')
            return value

        def _from_wsgi_str(self, value):
            if isinstance(value, unicode):
                value = value.encode('latin-1')
            return value

    # The HTTP method alone is a string, not bytes.
    @property
    def method(self):
        return self.environ.get('REQUEST_METHOD', 'GET')

    @method.setter
    def method(self, val):
        if PY3:
            if isinstance(val, bytes):
                val = val.decode('latin-1')
        else:
            if isinstance(val, unicode):
                val = val.encode('latin-1')

        self.environ['REQUEST_METHOD'] = val

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
    del _headers_getter, _headers_setter

    input_stream = _environ_prop('wsgi.input')


@property_overriding
class WSGIRequest(WSGIBaseRequest):
    _STRIP_PORT = re.compile(br":\d+\Z")

    def __init__(self, *args, **kwargs):
        super(WSGIRequest, self).__init__(*args, **kwargs)

    @oproperty
    def path_info(self, orig):
        """
        An override of path_info's getter that ensures we always have a
        leading slash.
        """
        val = orig()
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

    # TODO: do we want to go to the trouble of creating the host+port above,
    # and also split it here?  It seems like extra work.
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
        """The full URL of the request."""
        # This code adapted from PEP 3333, thanks to Ian Bicking.
        url = self.scheme + b'://'

        url += self.host_with_port

        path = b'/' + self.path.lstrip(b'/')

        url += quote(path)
        if len(self.query_string) > 0:
            url += b'?' + self.query_string

        return url

    def __str__(self):
        parts = [self.method + b' ' +
                 self.full_path + b' ' +
                 self.http_version]

        for k, v in sorted(self.headers.items()):
            parts.append(k + b': ' + v)

        return b"\r\n".join(parts)


# TODO: do we really want this as a mixin?
class RequestVarsMixin(object):
    def __init__(self, *args, **kwargs):
        self.urlargs = []
        self.urlvars = {}
        super(RequestVarsMixin, self).__init__(*args, **kwargs)


from .mixins.accept import WSGIAcceptMixin
from .mixins.cache import WSGIRequestCacheMixin
from .mixins.date import WSGIRequestDateMixin
from .mixins.etag import WSGIRequestEtagMixin
from .mixins.request_building import WSGIRequestBuilderMixin

class WSGIFullRequest(WSGIAcceptMixin, WSGIRequestCacheMixin, RequestVarsMixin,
                      WSGIRequestEtagMixin, WSGIRequestDateMixin,
                      WSGIRequestBuilderMixin, WSGIRequest):
    pass
