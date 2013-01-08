from __future__ import with_statement, absolute_import, print_function

import re
import time
import string
import logging
from numbers import Number
from datetime import date, datetime, timedelta

from hoboken.six import text_type
from hoboken.objects.util import caching_property

# Get logger for this module.
logger = logging.getLogger(__name__)


# Regexes.  These are adapted from the standard library's cookie module.
SPECIAL_CHARS = b"~!@#$%^&*()_+=-`.?|:/(){}<>'"
LEGAL_CHAR_RE = b"[\w\d" + re.escape(SPECIAL_CHARS) + b"]"
COOKIE_RE = re.compile(
    br"(?x)"                            # This is a Verbose pattern
    br"(?P<name>"                       # Start of group 'key'
    b"" + LEGAL_CHAR_RE + b"+?"         # Any word of at least one letter, nongreedy
    br")"                               # End of group 'key'
    br"\s*=\s*"                         # Equal Sign
    br"(?P<val>"                        # Start of group 'val'
    br'"(?:[^\\"]|\\.)*"'               # Any doublequoted string
    br"|"                               # or
    br"\w{3},\s[\s\w\d-]{9,11}\s[\d:]{8}\sGMT" # Special case for "expires" attr
    br"|"                               # or
    b"" + LEGAL_CHAR_RE + b"*"          # Any word or empty string
    br")"                               # End of group 'val'
    br"\s*;?"                           # Probably ending in a semi-colon
)

# Renaming array.  This mapping converts from a lower-case representation to
# the traditional mixed-case formatting.  Also from the standard library.
_rename_mapping = {
    'expires': 'expires',
    'path': 'Path',
    'comment': 'Comment',
    'domain': 'Domain',
    'max-age': 'Max-Age',
    'secure': 'secure',
    'httponly': 'HttpOnly',
    'version': 'Version',
}

# Reserved names are the names in our rename array.
_reserved_names = frozenset(_rename_mapping.keys())

# Weekdays and months.  See comment in serialize_cookie_date for why we need
# these.
weekdays = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
months = (None, 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep',
          'Oct', 'Nov', 'Dec')


def parse_cookie(data, pattern=COOKIE_RE):
    i = 0
    n = len(data)
    morsel = None
    morsels = {}

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

        elif name.lower() in RESERVED_NAMES:
            if morsel:
                morsel[name] = value

        else:
            # Try and get the morsel, and if it doesn't exist, create it.
            morsel = morsels.get(name)
            if morsel is None:
                morsel = Morsel(name, value)
                morsels[name] = morsel
            else:
                logger.warn("Overwriting cookie value for morsel named: %r "
                            "(%r -> %r)", name, morsel.value, value)
                morsel.value = value

    # Return our morsels.
    return morsels


class CookieError(Exception):
    """
    An exception representing an error in cookie parsing.
    """
    pass


def _morsel_property(key, serializer=lambda v: v):
    def setter(self, val):
        self.attributes[key] = serializer(val)

    return property(lambda self: self.attributes.get(key), setter)


def serialize_max_age(val):
    if isinstance(val, timedelta):
        val = str(int(val.total_seconds()))
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
        val = datetime.utcnow() + val
    if isinstance(val, (datetime, date)):
        val = val.timetuple()

    # NOTE: We manually fill in the weekday and month here, since using the
    # '%a' or '%b' format for strftime is locale-dependent, and HTTP requires
    # using the US locale's names.
    ret = time.strftime('%%s, %d-%%s-%Y %H:%M:%S GMT', val)
    return (val % (weekdays[val[6]], months[val[1]])).encode('ascii')


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

    def __setitem__(self, key, value):
        self.attributes[key] = value

    def serialize(self, full=True):
        pass

    def __repr__(self):
        return "%s(name=%r, value=%r)" % (self.__class__.__name__, self.name,
                                          self.value)


class WSGICookiesMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGICookiesMixin, self).__init__(*args, **kwargs)
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


# TODO:
#   - Check for valid names
#   - Serialization support
#   - Tests!
