from __future__ import with_statement, absolute_import, print_function

import re
from . import six

UNSAFE_RE = re.compile(br"[^\\-_.!~*'();/?:@&=+$,\[\]a-zA-Z\d]")
ESCAPED_RE = re.compile(br"%[a-fA-F\d]{2}")

def quote(val, encoding='utf-8', unsafe=UNSAFE_RE):
    if isinstance(val, six.text_type):
        val = val.encode(encoding)

    if isinstance(unsafe, six.text_type):
        unsafe = unsafe.encode('latin1')

    if isinstance(unsafe, six.binary_type):
        pattern = b"[" + re.escape(unsafe) + b"]"
        unsafe = re.compile(pattern)

    def _quoter(match_obj):
        ch = match_obj.group(0)
        ech = "%{:02X}".format(ord(ch)).encode('ascii')
        return ech

    quoted = unsafe.sub(_quoter, val)
    return quoted


def unquote(val, encoding='utf-8'):
    if isinstance(val, six.text_type):
        val = val.encode(encoding)

    def _unquoter(match_obj):
        enc = match_obj.group(0)
        val = int(enc[1:], 16)
        return bytes([val])

    unquoted = ESCAPED_RE.sub(_unquoter, val)
    return unquoted
