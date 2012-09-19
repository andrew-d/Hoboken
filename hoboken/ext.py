from .application import HobokenBaseApplication
from .helpers import *
import re
import sys
try:
    import json
except ImportError:
    import simplejson as json

from .six import PY3, string_types, binary_type, text_type, iteritems


class HobokenJsonApplication(HobokenBaseApplication, HobokenCachingMixin, HobokenRedirectMixin):
    """
    This application class will convert returned values into JSON, properly escaping them.
    """
    def __init__(self, *args, **kwargs):
        super(HobokenJsonApplication, self).__init__(*args, **kwargs)

        if 'json_indent' not in self.config:
            self.config.json_indent = 4

        if 'json_escape' not in self.config:
            self.config.json_escape = True

        if 'json_wrap' not in self.config:
            self.config.json_wrap = True

    def _byte_to_hex(self, val, fill=2):
        return hex(val)[2:].zfill(fill).upper()

    def recursive_escape(self, value):
        if isinstance(value, dict):
            new_value = dict((self.recursive_escape(k), self.recursive_escape(v)) for k, v in iteritems(value))
        elif isinstance(value, list):
            new_value = list(self.recursive_escape(x) for x in value)
        elif isinstance(value, tuple):
            new_value = tuple(self.recursive_escape(x) for x in value)
        else:
            # Need to check for different string types on different versions of Python.
            if isinstance(value, string_types):
                regex = re.compile('[</>]')
                prefix = '\\u'
            elif isinstance(value, binary_type):        # pragma: no cover
                regex = re.compile(b'[</>]')
                prefix = b'\\u'
            else:
                # Not anything we want to escape, so just return the value
                # as-is without modification.
                return value

            def string_escaper(m):
                val = m.group(0)
                escaped = self._byte_to_hex(ord(val), fill=4)
                if PY3 and isinstance(val, bytes):      # pragma: no cover
                    escaped = escaped.encode('latin-1')
                return prefix + escaped

            new_value = regex.sub(string_escaper, value)

        return new_value


    def on_returned_body(self, request, resp, value):
        if not isinstance(value, dict):
            if self.config.json_wrap:
                value = {"value": value}
            else:
                # If we haven't been told to, we don't wrap the returned value,
                # and just set the body as-is.  We don't touch the
                # Content-Type, either.
                resp.body = value
                return

        # Escape if specified.
        if self.config.json_escape:
            value = self.recursive_escape(value)

        # Dump the value.
        dumped_value = json.dumps(value, indent=self.config.json_indent) + "\n"

        resp.body = dumped_value
        resp.content_type = 'application/json'

