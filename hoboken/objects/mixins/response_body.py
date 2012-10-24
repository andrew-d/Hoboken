from __future__ import with_statement, absolute_import, print_function

from ..util import cached_property, ssuper
from . import six


class ResponseBodyMixin(object):
    def __init__(self, *args, **kwargs):
        super(ResponseBodyMixin, self).__init__(*args, **kwargs)

    @property
    def response_iter(self):
        return super(ResponseBodyMixin, self).response_iter

    @response_iter.setter
    def response_iter(self, val):
        if isinstance(val, six.binary_type):
            # If this is a bytestring, we wrap it in a list.
            new_val = [val]
        elif hasattr(val, 'read') and six.callable(val.read):
            # This is a file-like object.  Read it, and wrap the response in an
            # iterable.
            new_val = [val.read()]
        else:
            new_val = val

        # We need to use 'ssuper' to be able to call __set__.
        ssuper(ResponseBodyMixin, self).response_iter = new_val

