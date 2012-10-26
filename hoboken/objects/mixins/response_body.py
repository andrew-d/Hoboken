from __future__ import with_statement, absolute_import, print_function

from hoboken.objects.util import cached_property, ssuper, iter_close
from hoboken.six import binary_type, callable


class ResponseBodyMixin(object):
    def __init__(self, *args, **kwargs):
        super(ResponseBodyMixin, self).__init__(*args, **kwargs)

    @property
    def response_iter(self):
        return super(ResponseBodyMixin, self).response_iter

    @response_iter.setter
    def response_iter(self, val):
        if isinstance(val, binary_type):
            # If this is a bytestring, we wrap it in a list.
            new_val = [val]
        elif hasattr(val, 'read') and callable(val.read):
            # This is a file-like object.  Read it, and wrap the response in an
            # iterable.
            new_val = [val.read()]
        else:
            new_val = val

        # We need to use 'ssuper' to be able to call __set__.
        ssuper(ResponseBodyMixin, self).response_iter = new_val

    @property
    def body_file(self):
        """The response body as a file-like object."""
        # TODO: implement
        # TODO: do we want to have our response_iter handle file-like objects,
        # or have it as a body_file.setter?
        pass

