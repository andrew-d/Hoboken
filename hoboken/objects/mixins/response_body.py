from __future__ import with_statement, absolute_import, print_function

import logging

from hoboken.objects.oproperty import oproperty, property_overriding
from hoboken.six import advance_iterator, binary_type, text_type


logger = logging.getLogger(__name__)


class IteratorFile(object):
    """
    This class converts an iterator into a file-like object.
    TODO: Look into inheriting from RawIOBase or something similar.
    """
    def __init__(self, it):
        self.iter = iter(it)
        self.last_chunk = b''
        self._closed = False

    @property
    def closed(self):
        return self._closed

    def readall(self):
        if self._closed:
            return b''

        val = b''.join(self.iter)
        self._closed = True
        return self.last_chunk + val

    def read(self, size=-1):
        if size == -1:
            return self.readall()

        chunks = [self.last_chunk]
        total_size = len(self.last_chunk)
        self.last_chunk = b''

        # If we're not closed, read chunks from the iterator until we have
        # enough data.
        if not self._closed:
            try:
                while total_size < size:
                    curr_chunk = advance_iterator(self.iter)
                    chunks.append(curr_chunk)
                    total_size += len(curr_chunk)
            except StopIteration:
                self._closed = True

        # Make return value
        return_val = b''.join(chunks)

        # Trim the returned size, if necessary.
        if len(return_val) > size:
            return_val, self.last_chunk = return_val[:size], return_val[size:]

        # Return it!
        return return_val


@property_overriding
class ResponseBodyMixin(object):
    def __init__(self, *args, **kwargs):
        super(ResponseBodyMixin, self).__init__(*args, **kwargs)

    @oproperty.override_setter
    def response_iter(self, val, orig):
        # If this is a bytestring, we wrap it in a list.
        if isinstance(val, binary_type):
            new_val = [val]
        else:
            new_val = val

        # Call the original setter with our new value.
        orig(new_val)

    @property
    def body_file(self):
        """The response body as a file-like object."""
        return IteratorFile(self.response_iter)

    @body_file.setter
    def body_file(self, val):
        it = [val.read()]
        self.response_iter = it

    @property
    def body(self):
        """
        The body as a bytestring.
        """
        return b''.join(self.response_iter)

    @body.setter
    def body(self, val):
        if not isinstance(val, binary_type):
            logger.error("Response body must be set to a bytestring")
            raise ValueError("Response body must be set to a bytestring")

        self.response_iter = [val]

    @property
    def text(self):
        """
        The body as a Unicode string.
        """
        # TODO: benchmark these options
        # return u('').join(x.decode(self.charset) for x in self.response_iter)
        # return b''.join(self.response_iter).encode(self.charset)
        return self.body.decode(self.charset)

    @text.setter
    def text(self, val):
        if not isinstance(val, text_type):
            msg = "Response text must be set to a '%r' value".format(
                text_type.__name__
            )
            logger.error(msg)
            raise ValueError(msg)

        self.response_iter = [val.encode(self.charset)]
