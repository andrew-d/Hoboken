from __future__ import with_statement, absolute_import, print_function

import re
import time
import calendar
from datetime import (
    date,
    datetime,
    timedelta
)
from email.utils import (
    parsedate_tz,
    mktime_tz,
    formatdate
)
from numbers import Number
from hoboken.six import binary_type, text_type


def date_header_property(header, read_only=False):
    def getter(self):
        return self._parse_date(self.headers.get(header))
    def setter(self, value):
        if value is None:
            self.headers.pop(header, None)
        else:
            self.headers[header] = self._serialize_date(value)
    def deleter(self):
        self.headers.pop(header, None)

    # TODO: Set the docstring properly
    if read_only:
        return property(getter, doc='')
    else:
        return property(getter, setter, deleter, doc='')


class WSGIDateMixin(object):
    """
    This mixin is used for both Requests and Responses.
    """

    def __init__(self, *args, **kwargs):
        super(WSGIDateMixin, self).__init__(*args, **kwargs)

    # Hook for datetime.now - makes testing easier.
    __now = staticmethod(datetime.now)

    def _parse_date(self, value):
        """
        Parse a given date string into a datetime() value.
        """
        if value is None:
            return None

        if isinstance(value, binary_type):
            value = value.decode('latin-1')

        tup = parsedate_tz(value)
        if tup is None:
            return None

        # If no timezone is given, we assume UTC time.
        if tup[-1] is None:
            tup = tup[:9] + (0,)

        timestamp = mktime_tz(tup)
        return datetime.utcfromtimestamp(timestamp)

    def _serialize_date(self, value):
        """
        Serialize a date into an RFC 2822-compliant binary string.
        """
        # If we're given a string, we return it as-is.
        if isinstance(value, binary_type):
            return value
        if isinstance(value, text_type):
            return value.encode('latin-1')

        # If we're given a time delta, we assume it's from now.
        if isinstance(value, timedelta):
            value = self.__now() + value

        # If we have a date/datetime, we make it into a tuple.
        if isinstance(value, (date, datetime)):
            value = value.timetuple()

        # Now, if we have a tuple of some sort, convert to an int.
        if isinstance(value, (tuple, time.struct_time)):
            value = calendar.timegm(value)

        # Finally, assert that we actually have an number by this point.
        if not isinstance(value, Number):
            raise ValueError("Unknown value to serialize: {0!r}".format(value))

        # Note: The 'usegmt' argument will put 'GMT' after the date, instead of
        # the string '-0000'.
        serialized = formatdate(value, usegmt=True)
        return serialized.encode('latin-1')

    date = date_header_property('Date')


class WSGIResponseDateMixin(WSGIDateMixin):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseDateMixin, self).__init__(*args, **kwargs)

    last_modified = date_header_property('Last-Modified')
    expires = date_header_property('Expires')


class WSGIRequestDateMixin(WSGIDateMixin):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestDateMixin, self).__init__(*args, **kwargs)

    if_modified_since = date_header_property('If-Modified-Since')
    if_unmodified_since = date_header_property('If-Unmodified-Since')

