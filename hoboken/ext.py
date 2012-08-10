from .application import HobokenBaseApplication
from .helpers import *
import re
import sys
try:
    import json
except:
    import simplejson as json


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

    def _byte_to_hex(self, val, fill=2):
        return hex(val)[2:].zfill(fill).upper()

    def recursive_escape(self, value):
        if isinstance(value, dict):
            new_value = {}
            for key in value:
                escaped_key = self.recursive_escape(key)
                escaped_value = self.recursive_escape(value[key])

                new_value[escaped_key] = escaped_value
        elif isinstance(value, list):
            new_value = list(recursive_escape(x) for x in value)
        elif isinstance(value, tuple):
            new_value = tuple(recursive_escape(x) for x in value)
        else:
            # Need to check for different string types on different versions of Python.
            if sys.version_info[0] >= 3:
                if isinstance(value, bytes):
                    regex = re.compile(b'[</>]')
                    prefix = b'\\u'
                elif isinstance(value, str):
                    regex = re.compile('[</>]')
                    prefix = '\\u'
            else:
                if isinstance(value, basestring):
                    regex = re.compile('[</>]')
                    prefix = '\\u'

            def string_escaper(m):
                val = m.group(0)
                return prefix + self._byte_to_hex(ord(val), fill=4)

            new_value = regex.sub(string_escaper, value)

        return new_value


    def on_returned_body(self, request, resp, value):
        if not isinstance(value, dict):
            value = {"value": value}

        # Escape if specified.
        if self.config.json_escape:
            value = self.recursive_escape(value)

        # Dump the value.
        dumped_value = json.dumps(value, indent=self.config.json_indent) + "\n"
        if sys.version_info[0] >= 3:
            dumped_value = dumped_value.encode('latin-1')

        resp.body = dumped_value
        resp.content_type = 'application/json'

