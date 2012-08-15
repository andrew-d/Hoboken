from __future__ import with_statement, absolute_import, print_function
import re
from collections import MutableMapping
from .base import BaseRequest
from .util import *
from ..six import *


class WSGIHeaders(MutableMapping):
    def __init__(self, environ):
        self.environ = environ

    def _realname(self, name):
        name = name.upper()
        return 'HTTP_' + name.replace('-', '_')

    def __getitem__(self, name):
        return self.environ[self._realname(name)]

    def __setitem__(self, name, value):
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
            if isinstance(key, string_types) and key.startswith('HTTP_'):
                yield key[5:].replace('_', '-').title()


class WSGIBaseRequest(BaseRequest):
    def __init__(self, environ):
        super(WSGIBaseRequest, self).__init__()
        if type(environ) is not dict:
            raise ValueError("The WSGI environ must be a dict, not a {0}".format(type(environ)))

        self.environ = environ

    method = _environ_prop('REQUEST_METHOD', 'GET')
    scheme = _environ_prop('wsgi.url_scheme')
    script_name = _environ_prop('SCRIPT_NAME')
    path_info = _environ_prop('PATH_INFO')
    query_string = _environ_prop('QUERY_STRING')
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


class WSGIRequest(object):
    @property
    def path_info(self):
        """An override of path_info that ensures we always have a leading
        slash.
        """
        val = super(WSGIRequest, self).path_info()
        return '/' + val.lstrip('/')

    @property
    def host_with_port(self):
        if self.environ.get('HTTP_HOST'):
            return self.environ['HTTP_HOST']
        else:
            host = self.environ['SERVER_NAME']

            if self.scheme == 'https':
                if self.port != '443':
                   host += ':' + self.port
            else:
                if self.port != '80':
                   host += ':' + self.port
        return host

    @property
    def host(self):
        return self._STRIP_PORT.sub('', self.host_with_port)

    @property
    def port(self):
        spl = self.host_with_port.split(':')
        if len(spl) > 1:
            return int(spl[1])

        if self.environ.get('HTTP_X_FORWARDED_PORT'):
            return int(self.environ['HTTP_X_FORWARDED_PORT'])

        if self.scheme == 'https':
            return 443
        # elif 'HTTP_X_FORWARDED_HOST' in 

    @property
    def path(self):
        return self.script_name + self.path_info

    @property
    def url(self):
        """ The full URL of the request."""
        # This code taken from PEP 3333, thanks to Ian Bicking.
        url = self.scheme + '://'

        url += self.host_with_port

        url += quote(environ.get('SCRIPT_NAME', ''))
        url += quote(environ.get('PATH_INFO', ''))
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']

        return url

    @property
    def secure(self):
        return self.scheme == 'https'


