from __future__ import with_statement, absolute_import, print_function

import re
from . import six

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
    QUOTE_RE = re.compile(r'[^a-zA-Z0-9._-]')
    # TOKEN_RE = re.compile(
    #                       r'([a-zA-Z][a-zA-Z_-]*)           # The directive name'
    #                       r'\s*                             # Any amount of whitespace'
    #                       r'(?:=                            # Equals sign'
    #                       r'  (?:"([^"]*)"|([^ \t",;]*))    # Either a quoted value, or some string of chars without whitespace or quotes'
    #                       r')?                              # Value is optional'
    #                      , re.VERBOSE)
    TOKEN_RE = re.compile(r'([a-zA-Z][a-zA-Z_-]*)\s*(?:=(?:"([^"]*)"|([^ \t",;]*)))?')


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

            value = str(value)
            if self.QUOTE_RE.search(value):
                value = '"{0}"'.format(value)

            parts.append("{0}={1}".format(name, value))

        return ', '.join(parts)

    @classmethod
    def parse(klass, http_obj, header_value):
        properties = klass.parse_value(header_value)
        return klass(http_obj, initial_properties=properties)

    @staticmethod
    def parse_value(value):
        properties = {}
        for match in klass.TOKEN_RE.finditer(header_value):
            print(repr(match.groups()))
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
        return 'CacheObject("{0}")'.format(self._serialize_cache_control())


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
    no_cache = _boolean_property('no-cache')
    no_store = _boolean_property('no-store')
    no_transform = _boolean_property('no-transform')
    must_revalidate = _boolean_property('must-revalidate')
    proxy_revalidate = _boolean_property('proxy-revalidate')

    private = _value_property('private')
    max_age = _value_property('max-age')
    s_max_age = _value_property('s-maxage')

class WSGICacheMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIAcceptMixin, self).__init__(*args, **kwargs)
        self._cache_object = CacheObject(self)

    @property
    def cache_control(self):
        return self._cache_object

    # TODO:
    #   - Need to handle request vs. response directives
    #   - Accessors like, e.g.: response.cache.max_age = 1234, or request.cache.no_cache = True
    #   - The 'Age' HTTP header
    #   - The 'Expires' HTTP header
    #   - 'Pragma: no-cache' --> 'Cache-Control: no-cache'
    #   - The 'Vary' HTTP header
    #   - 

