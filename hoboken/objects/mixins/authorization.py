from __future__ import with_statement, absolute_import, print_function

import re
import base64

from hoboken.six import iteritems

valid_authentication_schemes = ['Basic', 'Digest', 'WSSE', 'HMACDigest',
                                'GoogleLogin', 'Cookie', 'OpenID']
_valid_schemes_set = set(valid_authentication_schemes)

AUTH_PARAMS_REGEX = re.compile(br'([a-z]+)=(".*?"|[^,]*)(?:\Z|, *)')


class Authorization(object):
    def __init__(self, type, params):
        self.type = type
        self.params = params

    @classmethod
    def parse(klass, val):
        if val is None:
            return None

        authtype, params = val.split(' ', 1)
        if authtype in _valid_schemes_set:
            if authtype == 'Basic' and '"' not in params:
                params = klass._parse_basic_auth(params)
            else:
                params = klass._parse_auth_params(params)

        return klass(authtype, params)

    @classmethod
    def _parse_auth_params(klass, params):
        ret = {}
        for k, v in AUTH_PARAMS_REGEX.findall(params):
            ret[k] = v.strip('"')
        return ret

    @classmethod
    def _parse_basic_auth(klass, value):
        try:
            dec = base64.b64decode(value)
            if not b':' in dec:
                return value

            username, password = dec.split(b':', 1)
            return {b'username': username, b'password': password}
        except TypeError:
            return value

    def serialize(self):
        if (self.type == b'Basic' and
            sorted(self.params.keys()) == [b'password', b'username']):
            v = self.params[b'username'] + b':' + self.params[b'password']
            enc = base64.b64encode(v)

            return b'Basic ' + enc
        else:
            p = []
            for k, v in iteritems(self.params):
                p.append(k + b'="' + v + b'"')

            return self.type + b' ' + b', '.join(p)


class WSGIRequestAuthorizationMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestAuthorizationMixin, self).__init__(*args, **kwargs)

    @property
    def authorization(self):
        return Authorization.parse(self.headers.get('Authorization'))


class WSGIResponseAuthorizationMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseAuthorizationMixin, self).__init__(*args, **kwargs)

    @property
    def www_authenticate(self):
        return Authorization.parse(self.headers.get('WWW-Authenticate'))

