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

        # Dump the value.
        dumped_value = json.dumps(value, indent=self.config.json_indent) + "\n"

        # Escape if specified.
        if self.config.json_escape:
            # The escape here is fairly hacky, since Python doesn't let us
            # override the encoding of built-in objects.
            dumped_value = self.escape_string(dumped_value)

        resp.body = dumped_value
        resp.content_type = 'application/json'

    def escape_string(self, string):
        escapes = {'&': '\\u0026', '>': '\\u003E', '<': '\\u003C'}
        def encoder(match):
            v = match.group(0)
            return escapes[v]

        return re.sub(r"[&<>]", encoder, string)

