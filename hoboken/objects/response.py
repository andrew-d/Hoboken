from __future__ import with_statement, absolute_import, print_function
import re
from numbers import Number
import collections

from hoboken.objects.base import BaseResponse
from hoboken.objects.headers import WSGIHeaders
from hoboken.objects.constants import status_reasons, status_generic_reasons
from hoboken.util import iter_close


class WSGIBaseResponse(BaseResponse):
    def __init__(self, charset='utf-8', *args, **kwargs):
        super(WSGIBaseResponse, self).__init__(*args, **kwargs)

        self._status_code = 200
        self._response_iter = [b'']
        self.charset = charset

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
            text = status_generic_reasons[self._status_code]
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

        self._response_iter = val

    def close(self):
        iter_close(self._response_iter)


from .mixins.response_body import ResponseBodyMixin

class WSGIFullResponse(ResponseBodyMixin, WSGIBaseResponse):
    pass

