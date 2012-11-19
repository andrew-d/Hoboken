from __future__ import with_statement, absolute_import, print_function
import re
from numbers import Number
import collections

from hoboken.objects.base import BaseResponse
from hoboken.objects.headers import WSGIHeaders
from hoboken.objects.constants import status_reasons, status_generic_reasons
from hoboken.objects.util import iter_close


class EmptyResponse(object):
    """
    An empty WSGI response.

    An iterator that immediately stops. Optionally provides a close
    method to close the underlying response_iter it replaces.
    """

    def __init__(self, response_iter=None):
        if response_iter and hasattr(response_iter, 'close'):
            self.close = response_iter.close

    def __iter__(self):
        return self

    def __len__(self):
        return 0

    def next(self):
        raise StopIteration()

    # For Python 3.X
    __next__ = next


class WSGIBaseResponse(BaseResponse):
    def __init__(self, charset='utf-8', *args, **kwargs):
        self.charset = charset

        self._status_code = kwargs.pop('status_int', 200)
        self._response_iter = [b'']

        super(WSGIBaseResponse, self).__init__(*args, **kwargs)

    @property
    def status_int(self):
        return self._status_code

    @status_int.setter
    def status_int(self, val):
        if not 100 <= val <= 599:
            raise ValueError("status_int must be a number between 100 and 599")
        self._status_code = val

    @property
    def status_text(self):
        text = status_reasons.get(self._status_code)
        if not text:
            text = status_generic_reasons[self._status_code / 100]
        return text

    @property
    def status(self):
        return str(self._status_code) + " " + self.status_text

    @status.setter
    def status(self, val):
        spl = val.split(" ")[0]
        self.status_int = int(spl)


    _headers = None
    def _headers_getter(self):
        if self._headers is None:
            self._headers = WSGIHeaders({})
        return self._headers

    def _headers_setter(self, value):
        self.headers.clear()
        self.headers.update(value)

    headers = property(_headers_getter, _headers_setter)

    @property
    def response_iter(self):
        return self._response_iter

    @response_iter.setter
    def response_iter(self, val):
        # This thing should be iterable.
        if not isinstance(val, collections.Iterable):
            raise ValueError("Values assigned to response_iter must be "
                             "iterable, not {0!s}".format(type(val))
                             )

        self._response_iter = iter(val)

    def close(self):
        """Close the underlying iterator, if we need to."""
        iter_close(self._response_iter)

    def __call__(self, environ, start_response):
        header_list = self.headers.to_list()
        start_response(self.status, header_list)

        # We special-case the HEAD method to return an empty response.
        if environ['REQUEST_METHOD'] == 'HEAD':
            return EmptyResponse(self.response_iter)

        return self.response_iter



from .mixins.cache import WSGIResponseCacheMixin
from .mixins.date import WSGIResponseDateMixin
from .mixins.etag import WSGIResponseEtagMixin
from .mixins.response_body import ResponseBodyMixin

class WSGIFullResponse(ResponseBodyMixin, WSGIResponseCacheMixin,
                       WSGIResponseEtagMixin, WSGIResponseDateMixin,
                       WSGIBaseResponse):
    pass

