import re
import sys
try:
    import json
except ImportError:
    import simplejson as json

from hoboken.six import PY3, string_types, binary_type, text_type, u, iteritems
from hoboken.application import HobokenBaseApplication
from hoboken.helpers import *


class HobokenJsonApplication(HobokenBaseApplication, HobokenCachingMixin, HobokenRedirectMixin):
    """
    This application class will convert returned values into JSON, properly escaping them.
    """
    def __init__(self, *args, **kwargs):
        super(HobokenJsonApplication, self).__init__(*args, **kwargs)

        self.config.setdefault('JSON_INDENT', 4)
        self.config.setdefault('JSON_ESCAPE', True)
        self.config.setdefault('JSON_WRAP', True)

    def on_returned_body(self, request, resp, value):
        if not isinstance(value, dict):
            if self.config['JSON_WRAP']:
                value = {"value": value}
            else:
                # If we haven't been told to, we don't wrap the returned value,
                # and just set the body as-is.  We don't touch the
                # Content-Type, either.
                resp.body = value
                return

        # Dump the value.
        dumped_value = json.dumps(value, indent=self.config['JSON_INDENT']) + "\n"

        # Escape if specified.
        if self.config['JSON_ESCAPE']:
            # The escape here is fairly hacky, since Python doesn't let us
            # override the encoding of built-in objects.
            dumped_value = self.escape_string(dumped_value)

        resp.body = dumped_value
        resp.content_type = 'application/json'

    def escape_string(self, string):
        base_escapes = {
            b'&': b'\\u0026', b'>': b'\\u003E', b'<': b'\\u003C'
        }
        escapes = base_escapes.copy()
        for k, v in iteritems(base_escapes):
            escapes[k.decode('latin-1')] = v.decode('latin-1')

        # Decode our unicode line/paragraph seperators.
        line_sep = b'\xE2\x80\xA8'.decode('utf-8')
        line_sep_escape = b'\\u2028'.decode('latin-1')
        paragraph_sep = b'\xE2\x80\xA9'.decode('utf-8')
        paragraph_sep_escape = b'\\u2029'.decode('latin-1')

        def encoder(match):
            v = match.group(0)
            return escapes[v]

        if isinstance(string, text_type):
            ret = re.sub(u(r"[&<>]"), encoder, string)
            return ret.replace(line_sep, line_sep_escape).replace(
                paragraph_sep, paragraph_sep_escape)
        else:
            return re.sub(br"[&<>]", encoder, string)

