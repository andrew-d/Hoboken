from __future__ import with_statement, absolute_import, print_function

import re
from numbers import Number
from . import six
from ..util import cached_property

class _boolean_property(object):
    def __init__(self, property_name):
        self.name = property_name

    def __get__(self, obj, type=None):
        val = obj.get_property(self.name)
        if val is None:
            val = False
        return val

    def __set__(self, obj, val):
        obj.set_property(self.name, val)

    def __delete__(self, obj):
        obj.set_property(self.name, False)

class _value_property(object):
    def __init__(self, property_name):
        self.name = property_name

    def __get__(self, obj, type=None):
        return obj.get_property(self.name)

    def __set__(self, obj, val):
        obj.set_property(self.name, val)

    def __delete__(self, obj):
        obj.set_property(self.name, None)


class CacheObject(object):
    QUOTE_RE = re.compile(br'[^a-zA-Z0-9._-]')
    TOKEN_RE = re.compile(
        br'([a-zA-Z][a-zA-Z_-]*)'   # The directive name
        br'\s*'                     # Any amount of whitespace
        br'(?:='                    # Equals sign
            br'(?:"([^"]*)"|'       # Either a quoted string...
            br'([^ \t",;]*))'       # ... or a non-quoted string.
        br')?'                      # Value is optional
    )

    def __init__(self, http_obj, initial_properties={}):
        self.http_obj = http_obj
        # self.underlying_header = http_obj.headers.get('Cache-Control')
        self.properties = initial_properties.copy()

    def get_property(self, name):
        return self.properties.get(name)

    def set_property(self, name, val):
        self.properties[name] = val

        header_val = self._serialize_cache_control()
        self.http_obj.headers['Cache-Control'] = header_val

    # TODO: figure out whether we want to use this
    # def _check_underlying_header(self):
    #     if self.underlying_header is self.http_obj.get('Cache-Control'):
    #         return

    #     # The underlying header value doesn't match.  Re-parse.
    #     new_

    def _serialize_cache_control(self):
        parts = []
        for name, value in sorted(self.properties.items()):
            if value is False:
                continue

            if value is True:
                parts.append(name)
                continue

            # Convert numbers to strings, and text (unicode/str) to bytes.
            if isinstance(value, Number):
                value = str(value)
            if isinstance(value, six.text_type):
                value = value.encode('latin-1')

            if self.QUOTE_RE.search(value):
                value = b'"' + value + b'"'

            parts.append(name + b'=' + value)

        return b', '.join(parts)

    @classmethod
    def parse(klass, http_obj, header_value):
        properties = klass.parse_value(header_value)
        return klass(http_obj, initial_properties=properties)

    @classmethod
    def parse_value(klass, header_value):
        properties = {}
        for match in klass.TOKEN_RE.finditer(header_value):
            name = match.group(1)
            value = match.group(2) or match.group(3) or None
            if value:
                try:
                    value = int(value)
                except ValueError:
                    pass
            else:
                value = True

            properties[name] = value

        return properties

    def __repr__(self):
        return 'CacheObject({0})'.format(self._serialize_cache_control())


class RequestCacheObject(CacheObject):
    # Valid request cache-control values.
    #   - no_cache
    #   - no_store
    #   - no_transform
    #   - max_age + value
    #   - max_stale + optional value
    #   - min_fresh + value
    #   - only_if_cached

    no_cache = _boolean_property('no-cache')
    no_store = _boolean_property('no-store')
    no_transform = _boolean_property('no-transform')
    only_if_cached = _boolean_property('only-if-cached')

    max_age = _value_property('max-age')
    max_stale = _value_property('max-stale')
    min_fresh = _value_property('min-fresh')


class ResponseCacheObject(CacheObject):
    # Valid response cache-control values.
    #   - public
    #   - private + optional value
    #   - no_cache + optional value
    #   - no_store
    #   - no_transform
    #   - max_age + value
    #   - s_max_age + value
    #   - must_revalidate
    #   - proxy_revalidate

    public = _boolean_property('public')
    no_cache = _boolean_property('no-cache')                # FIXME: this doesn't handle a value
    no_store = _boolean_property('no-store')
    no_transform = _boolean_property('no-transform')
    must_revalidate = _boolean_property('must-revalidate')
    proxy_revalidate = _boolean_property('proxy-revalidate')

    private = _value_property('private')
    max_age = _value_property('max-age')
    s_max_age = _value_property('s-maxage')
    s_maxage = s_max_age

class WSGIRequestCacheMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestCacheMixin, self).__init__(*args, **kwargs)

    @cached_property
    def cache_control(self):
        header_val = self.headers.get('Cache-Control', b'')
        cache_object = RequestCacheObject.parse(self, header_val)
        return cache_object

class WSGIResponseCacheMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseCacheMixin, self).__init__(*args, **kwargs)

    @cached_property
    def cache_control(self):
        header_val = self.headers.get('Cache-Control', b'')
        cache_object = ResponseCacheObject.parse(self, header_val)
        return cache_object

# TODO:
#   - The 'Age' HTTP header
#   - The 'Expires' HTTP header
#   - 'Pragma: no-cache' --> 'Cache-Control: no-cache'
#   - The 'Vary' HTTP header
#   - Investigate whether deleting a property works

