from __future__ import with_statement, absolute_import, print_function

import re
import base64
import logging
import binascii

from hoboken.six import binary_type, iteritems


logger = logging.getLogger(__name__)


# Note: some of below code inspired by the code from WebOb.  Thanks guys!
valid_authentication_schemes = [b'Basic', b'Digest', b'WSSE', b'HMACDigest',
                                b'GoogleLogin', b'Cookie', b'OpenID', b'Bearer'
                                ]
_valid_schemes_set = frozenset(valid_authentication_schemes)

AUTH_PARAMS_REGEX = re.compile(br'([a-z]+)=(".*?"|[^,]*)(?:\Z|, *)')


def _parse_auth_params(params):
    ret = {}
    for k, v in AUTH_PARAMS_REGEX.findall(params):
        ret[k] = v.strip(b'"')
    return ret


def parse_auth(val):
    if val is None:
        return None

    authtype, params = val.split(b' ', 1)
    if authtype in _valid_schemes_set:
        if authtype == b'Basic' and b'"' not in params:
            pass
        else:
            params = _parse_auth_params(params)

    return (authtype, params)


def serialize_auth(val):
    if isinstance(val, (tuple, list)):
        authtype, params = val
        if isinstance(params, dict):
            params = b', '.join(
                [k + b'="' + v + b'"' for k, v in iteritems(params)]
            )
        if not isinstance(params, binary_type):
            msg = "Invalid type for 'params': %s" % (params.__class__.__name__)
            logger.warn(msg)
            raise ValueError(msg)

        return authtype + b' ' + params

    return val


class WSGIRequestAuthorizationMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestAuthorizationMixin, self).__init__(*args, **kwargs)

    @property
    def authorization(self):
        return parse_auth(self.headers.get(b'Authorization'))

    @authorization.setter
    def authorization(self, val):
        self.headers[b'Authorization'] = serialize_auth(val)


class WSGIResponseAuthorizationMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseAuthorizationMixin, self).__init__(*args, **kwargs)

    @property
    def www_authenticate(self):
        return parse_auth(self.headers.get(b'WWW-Authenticate'))

    @www_authenticate.setter
    def www_authenticate(self, val):
        self.headers[b'WWW-Authenticate'] = serialize_auth(val)
