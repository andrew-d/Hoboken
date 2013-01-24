from __future__ import with_statement, absolute_import, print_function

import re
from hoboken.six import PY3, text_type, binary_type

# Quoting/unquoting regexes
UNSAFE_RE = re.compile(br"[^\\-_.!~*'();/?:@&=+$,\[\]a-zA-Z\d]")
ESCAPED_RE = re.compile(br"%[a-fA-F\d]{2}")

# These are regexes for parsing header values.
SPECIAL_CHARS = re.escape(b'()<>@,;:\\"/[]?={} \t')
QUOTED_STR = br'"(?:\\.|[^"])*"'
VALUE_STR = br'(?:[^' + SPECIAL_CHARS + br']+|' + QUOTED_STR + br')'
OPTION_RE_STR = (
    br'(?:;|^)\s*([^' + SPECIAL_CHARS + br']+)\s*=\s*(' + VALUE_STR + br')'
)
OPTION_RE = re.compile(OPTION_RE_STR)
QUOTE = b'"'[0]


def quote(val, encoding='utf-8', unsafe=UNSAFE_RE):
    if isinstance(val, text_type):
        val = val.encode(encoding)

    if isinstance(unsafe, text_type):
        unsafe = unsafe.encode('latin1')

    if isinstance(unsafe, binary_type):
        pattern = b"[" + re.escape(unsafe) + b"]"
        unsafe = re.compile(pattern)

    def _quoter(match_obj):
        ch = match_obj.group(0)
        ech = "%{v:02X}".format(v=ord(ch)).encode('ascii')
        return ech

    quoted = unsafe.sub(_quoter, val)
    return quoted


def unquote(val, encoding='utf-8'):
    if isinstance(val, text_type):
        val = val.encode(encoding)

    chars = []
    if PY3:             # pragma: no cover
        def _unquoter(match_obj):
            enc = match_obj.group(0)
            val = int(enc[1:], 16)
            return bytes([val])
    else:               # pragma: no cover
        def _unquoter(match_obj):
            enc = match_obj.group(0)
            val = int(enc[1:], 16)
            return chr(val)

    unquoted = ESCAPED_RE.sub(_unquoter, val)
    return unquoted


def parse_options_header(value):
    """
    Parses a Content-Type header into a value in the following format:
        (content_type, {parameters})
    """
    if not value:
        return (b'', {})

    # If we have no options, return the string as-is.
    if b';' not in value:
        return (value.lower().strip(), {})

    # Split at the first semicolon, to get our value and then options.
    ctype, rest = value.split(b';', 1)
    options = {}

    # Parse the options.
    for match in OPTION_RE.finditer(rest):
        key = match.group(1).lower()
        value = match.group(2)
        if value[0] == QUOTE and value[-1] == QUOTE:
            # Unquote the value.
            value = value[1:-1]
            value = value.replace(b'\\\\', b'\\').replace(b'\\"', b'"')

        # If the value is a filename, we need to fix a bug on IE6 that sends
        # the full file path instead of the filename.
        if key == b'filename':
            if value[1:3] == b':\\' or value[:2] == b'\\\\':
                value = value.split(b'\\')[-1]

        options[key] = value

    return ctype, options
