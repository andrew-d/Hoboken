from __future__ import with_statement, absolute_import, print_function

import re
from hoboken.six import text_type
from hoboken.objects.oproperty import property_overriding, oproperty


class WSGIRequestEtagMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestEtagMixin, self).__init__(*args, **kwargs)

    @property
    def if_match(self):
        pass

    @property
    def if_none_match(self):
        pass


class WSGIResponseEtagMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseEtagMixin, self).__init__(*args, **kwargs)

    @property
    def etag(self):
        # TODO: parse into objects that know how to do comparisons
        return self.headers.get('Etag')

    @etag.setter
    def etag(self, val):
        if isinstance(val, tuple):
            # The (etag, is_strong) case.
            pass
        elif isinstance(val, binary_type):
            # Just setting an etag.
            pass
        else:
            raise ValueError("You can only set an ETag to a binary value, or a"
                             "tuple in the form (etag, bool)")

