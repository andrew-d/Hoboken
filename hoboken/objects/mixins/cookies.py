from __future__ import with_statement, absolute_import, print_function

import re
import time
import string
import logging
from numbers import Number
from datetime import date, datetime, timedelta

from hoboken.six import iteritems, PY3, text_type
from hoboken.objects.util import caching_property
from hoboken.objects.datastructures import (
    CallbackMultiDictMixin,
    TranslatingMultiDict,
)

# Get logger for this module.
logger = logging.getLogger(__name__)


# Regexes.  These are adapted from the standard library's cookie module.
SPECIAL_CHARS = b"~!@#$%^&*()_+=-`.?|:/(){}<>'"
LEGAL_CHAR_RE = b"[\w\d" + re.escape(SPECIAL_CHARS) + b"]"
COOKIE_RE = re.compile(
    br"(?x)"                            # This is a Verbose pattern
    br"(?P<name>"                       # Start of group 'name'
    b"" + LEGAL_CHAR_RE + b"+?"         # Any word of at least one letter,
                                        # matching nongreedily
    br")"                               # End of group 'name'
    br"\s*=\s*"                         # Equal Sign
    br"(?P<val>"                        # Start of group 'val'
    br'"(?:[^\\"]|\\.)*"'               # Any doublequoted string
    br"|"                               # or
    br"\w{3},\s[\s\w\d-]{9,11}\s[\d:]{8}\sGMT"  # Special case for "expires"
    br"|"                               # or
    b"" + LEGAL_CHAR_RE + b"*"          # Any word or empty string
    br")"                               # End of group 'val'
    br"\s*;?"                           # Probably ending in a semicolon
)

# Regex for detecting quoted things.
QUOTED_RE = re.compile(br'\\([0-3][0-7][0-7]|.)')

# We use string.translate to quickly determine if something is valid.  These
# tables are used for that.
_noop_trans_table = b' ' * 256
_safe_chars = (string.ascii_letters + string.digits + "!#$%&'*+-.^_`|~/")
_safe_chars_bytes = _safe_chars.encode('ascii')

# Escape table.  For use in quoting a string.
_escape_table = dict((chr(i), '\\%03o' % i) for i in range(256))

# Update our escape table.  In order:
# 1. All safe characters are allowed, so we replace them with themselves.
_escape_table.update((x, x) for x in _safe_chars)

# 2. The characters ':' and ' ' can be used without escaping, too.
_escape_table[':'] = ':'
_escape_table[' '] = ' '

# 3. The escapes for quotes and slashes are special.
_escape_table['"'] = r'\"'
_escape_table['\\'] = r'\\'

# Finally, we might need to convert this table to operate on bytes, if we're
# on Python 3.
if PY3:     # pragma: no cover
    new = {}
    for k, v in iteritems(_escape_table):
        new[ord(k)] = v.encode('ascii')

    _escape_table = new

# This map is used to unquote things.  It contains two types of entries:
#   1. '101' --> 'A'        (octal --> single character)
#   2. 'A'   --> 'A'        (character -> same character)
_unquoter_table = dict(('%03o' % i, chr(i)) for i in range(256))
_unquoter_table.update((v, v) for v in list(_unquoter_table.values()))

# Convert to Python3 format if necessary
if PY3:
    new = {}
    for k, v in iteritems(_unquoter_table):
        new[k.encode('latin-1')] = v.encode('latin-1')

    _unquoter_table = new

# Renaming array.  This mapping converts from a lower-case representation to
# the traditional mixed-case formatting.  Also from the standard library.
_rename_mapping = {
    b'expires': b'expires',
    b'path': b'Path',
    b'comment': b'Comment',
    b'domain': b'Domain',
    b'max-age': b'Max-Age',
    b'secure': b'secure',
    b'httponly': b'HttpOnly',
    b'version': b'Version',
}

# Reserved names are the names in our rename array.
_reserved_names = frozenset(_rename_mapping.keys())

# Weekdays and months.  See comment in serialize_cookie_date for why we need
# these.
weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
months = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
          'Oct', 'Nov', 'Dec')


# This is a special function that we save for calculating the current time.
# It's useful for testing, when we want to mock out the dateime module.
_utcnow = datetime.utcnow


class CookieError(Exception):
    """
    An exception representing an error in cookie parsing.
    """
    pass


def _needs_quoting(value):
    # Since str objects don't have the second parameter to translate on
    # Python 3, we assert here (since it'll just crash below anyway)
    assert isinstance(value, bytes)

    # string.translate will replace all characters in the string with the
    # associated character in the first translation table, and remove all
    # characters in the second argument.  We use this to remove all 'safe'
    # characters from the string, and then replace all remaining characters
    # with spaces.  Then we can check if the string is empty - if not, then
    # there must have been an invalid character in the original string.
    return bool(value.translate(_noop_trans_table, _safe_chars_bytes))


def _quote(value):
    if _needs_quoting(value):
        value = b'"' + b''.join(map(_escape_table.__getitem__, value)) + b'"'
    return value


def _unquote(value):
    if isinstance(value, bool):
        return value

    if value[:1] == value[-1:] == b'"':
        value = value[1:-1]

    return QUOTED_RE.sub(_unquoter_func, value)


def _unquoter_func(match):
    return _unquoter_table[match.group(1)]


def parse_cookie(data, pattern=COOKIE_RE):
    i = 0
    n = len(data)
    morsel = None
    morsels = {}

    # Split all cookies.
    while 0 <= i <= n:
        # Search for a cookie.
        match = pattern.search(data, i)
        if not match:
            break

        # Get the name and value.
        name = match.group('name')
        value = match.group('val')

        # Move to the end of this match.
        i = match.end(0)

        # Parse the name.
        if name[0:1] == b'$':
            # TODO: handle cookie attributes?
            if morsel:
                morsel[name[1:]] = value

        elif name.lower() in _reserved_names:
            if morsel:
                morsel[name] = _unquote(value)

        else:
            # Try and get the morsel, and if it doesn't exist, create it.
            morsel = morsels.get(name)
            if morsel is None:
                morsel = Morsel(name, _unquote(value))
                morsels[name] = morsel
            else:
                logger.warn("Overwriting cookie value for morsel named: %r "
                            "(%r -> %r)", name, morsel.value, value)
                morsel.value = value

    # Return our morsels.
    return morsels


def _morsel_property(key, serializer=lambda v: v):
    def setter(self, val):
        self.attributes[key] = serializer(val)

    return property(lambda self: self.attributes.get(key), setter)


def serialize_max_age(val):
    if isinstance(val, timedelta):
        # Note: Python 2.6 doesn't have the 'total_seconds' attribute on a
        # timedelta object.  Thus, we simply calculate it ourselves.
        val = str(val.seconds + val.days * 24 * 3600)
    elif isinstance(val, Number):
        val = str(val)

    return val.encode('ascii')


def serialize_cookie_date(val):
    if val is None:
        return None
    elif isinstance(val, bytes):
        return val
    elif isinstance(val, text_type):
        return val.encode('ascii')
    elif isinstance(val, Number):
        val = timedelta(seconds=val)

    if isinstance(val, timedelta):
        val = _utcnow() + val
    if isinstance(val, (datetime, date)):
        val = val.timetuple()

    # NOTE: We manually fill in the weekday and month here, since using the
    # '%a' or '%b' format for strftime is locale-dependent, and HTTP requires
    # using the US locale's names.
    ret = time.strftime('%%s, %d-%%s-%Y %H:%M:%S GMT', val)
    return (ret % (weekdays[val[6]], months[val[1]])).encode('ascii')


class Morsel(object):
    """
    This class represents a single cookie as a key-value pair, with some
    additional attributes for cookie properties.
    """
    def __init__(self, name, value=b''):
        self.name = name
        self.value = value
        self.attributes = {}

    # RFC 2109 attributes
    path = _morsel_property(b'path')
    domain = _morsel_property(b'domain')
    comment = _morsel_property(b'comment')
    expires = _morsel_property(b'expires', serialize_cookie_date)
    max_age = _morsel_property(b'max-age', serialize_max_age)
    httponly = _morsel_property(b'httponly', bool)
    secure = _morsel_property(b'secure', bool)
    version = _morsel_property(b'version')

    def __setitem__(self, key, value):
        self.attributes[key.lower()] = value

    def serialize(self, full=True):
        result = []
        result.append(self.name + b'=' + _quote(self.value))
        if full:
            for key in [b'comment', b'domain', b'max-age', b'path',
                        b'version']:
                val = self.attributes.get(key)
                if val:
                    result.append(_rename_mapping[key] + b'=' + _quote(val))

            expires = self.attributes.get(b'expires')
            if expires:
                result.append(b'expires=' + expires)

            if self.secure:
                result.append(b'secure')

            if self.httponly:
                result.append(b'HttpOnly')

        return b'; '.join(result)

    def __eq__(self, other):
        if isinstance(other, Morsel):
            return (
                self.name == other.name and
                self.value == other.value and
                self.attributes == other.attributes
            )
        else:
            return NotImplemented

    def __repr__(self):
        return "%s(name=%r, value=%r)" % (self.__class__.__name__, self.name,
                                          self.value)


class CookiesDict(CallbackMultiDictMixin, TranslatingMultiDict):
    def __keytrans__(self, key):
        if PY3 and isinstance(key, str):
            key = key.encode('latin-1')

        return key


class WSGIRequestCookiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestCookiesMixin, self).__init__(*args, **kwargs)
        self.__cookies_header = None

    def __cookie_cache_func(self):
        return (self.__cookies_header is not None and
                self.__cookies_header is self.headers.get('Cookie'))

    @caching_property(__cookie_cache_func)
    def cookies(self):
        val = self.headers.get('Cookie')
        if not val:
            return {}

        # Parse all cookies
        morsels = parse_cookie(val)

        # Save our parsed cookies header for caching.  Note that this is done
        # after the parsing so that if an exception occurs, we don't cache
        # anything.
        self.__cookies_header = val
        return morsels


class WSGIResponseCookiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseCookiesMixin, self).__init__(*args, **kwargs)

        self.__cookies = CookiesDict()
        self.__cookies.on_change = self.__on_change

    def __on_change(self):
        # Remove all old Set-Cookie headers.
        self.headers.pop('Set-Cookie', None)

        # Update all new headers.
        for name, morsel in self.__cookies.iteritems(multi=True):
            # Encode the name properly.
            if PY3 and isinstance(name, str):
                name = name.encode('latin-1')

            # We reset the name on the morsel, since we assume that the name
            # in the cookies MultiDict wins.
            morsel.name = name

            # Serialize and set.
            val = morsel.serialize(full=True)
            self.headers.add('Set-Cookie', val)

    @property
    def cookies(self):
        return self.__cookies

    @cookies.setter
    def cookies(self, val):
        self.__cookies.clear()
        self.__cookies.update(val)

    @cookies.deleter
    def cookies(self):
        self.__cookies.clear()


# TODO:
#   - Check for valid names
#   - Setting (new) cookies is currently really broken
