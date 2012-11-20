from __future__ import with_statement, absolute_import, print_function

from hoboken.objects.util import cached_property, iter_close
from hoboken.six import binary_type, text_type, iteritems

try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs

from collections import namedtuple


def parse_content_type(value):
    """
    Parses a Content-Type header into a value in the following format:
        (content_type, {parameters})
    """
    if not value:
        return (b'', {})

    # Split by ";" character to grab the content type, and the rest.
    spl = value.split(b';')
    type, rest = spl[0], spl[1:]

    # If we only have the type, just exit.
    if not rest:
        return (type, {})

    # Ok, we need to decode the rest of the parameters.
    def _param_decoder(val):
        pass

    # TODO: properly parse and unquote the parameters now.
    params = {}
    for param in rest:
        key, val = param.split('=')
        params[key] = val

    return (type, params)


# Simple container for a (field_name, value) tuple.
Field = namedtuple('Field', ['name', 'value'])


# TODO: Fill this in with required stuff
# TODO: do we put file-size handling stuff here, and feed this class with
#       data, or do we let the parsers handle it?  I like the 1st option
class File(object):
    """
    This class represents an uploaded file.
    """
    def __init__(self, filename, mime=None):
        self.filename = filename
        self.mime = mime or 'application/octet-stream'


# TODO: Make this (and the other parsers) into classes with convenience
#       methods.  This will also let us track bytes consumed, and so on
def QuerystringParser():
    # Read until we get passed an empty buffer.
    buffer = []
    while True:
        val = yield None
        if len(val) == 0:
            break

        buffer.append(val)

    # We have a list of values here.  We concatenate them and parse.
    query_string = b''.join(buffer)
    fields = parse_qs(query_string)
    for name, val in iteritems(fields):
        yield ('field', Field(name, val))



def OctetStreamParser(filename, mime_type):
    # TODO: parse the octet-stream, return as File(...)
    pass







class RequestBodyMixin(object):
    def __init__(self, *args, **kwargs):
        super(RequestBodyMixin, self).__init__(*args, **kwargs)

        self.__bytes_received = 0
        self.__bytes_expected = 0

    # So, determining what to put here has been surprisingly difficult.
    # Currently, the plan is to support reading the entire body into memory
    # and storing it in the 'files' and 'form' dict, in addition to some sort
    # of streaming uploading, which will be the "base API".
    #
    # Things we might need:
    #   - Upload directory (for temp files)
    #   - Whether we should keep file extensions (default: False)
    #   - Maximum field size (not for files, default: 2MB)
    #   - Files:
    #       - Maximum possible size
    #       - Current received bytes for a file
    #       - More???
    #   - Tracking:
    #       - Bytes currently received
    #
    # Current plans.
    #   - Have a generator-based method which will yield tuples in the form:
    #       (event, data)
    #   - Feed the generator with data (with gen.send(data)) to attempt to move
    #     it to the next state.  Generator can yield None (or special event?)
    #     if it needs more data to continue parsing.
    #   - Generator will throw exception if there's a problem parsing.
    #   - Valid events are:
    #       - ('field', Field(...))         A form field was parsed
    #       - ('file', File(...))           A file field was parsed
    #       - None                          Need more data, please feed me
    #
    # Low-level example:
    #   parser = r.form_parser()
    #   try:
    #       parser.send(data)
    #       for event, object in parser:
    #           print("Got a '%r' with value: %r" % (event, object))
    #   except ValueError as ex:
    #       print("Error happened while parsing: %s" % (ex,))
    #   finally:
    #       parser.close()      # TODO: necessary?

    def form_parser(self):
        # Before we do anything else, we need to parse our Content-Type and
        # Content-Length headers.
        if 'Content-Length' in self.headers:
            # TODO: handle this if it fails.
            self.__bytes_expected = int(self.headers['Content-Length'])

        content_type = self.headers.get('Content-Type')
        if content_type is None:
            raise ValueError("No Content-Type header given!")

        content_type, params = parse_content_type(content_type)

        if content_type == 'application/octet-stream':
            pass
        elif (content_type == 'application/x-www-form-urlencoded' or
              content_type == 'application/x-url-encoded'):
            pass
        elif content_type == 'multipart/form-data':
            if not 'boundary' in params:
                raise ValueError("Bad Content-Type header: no boundary given")

            parser = QuerystringParser()
        else:
            raise ValueError("Unknown Content-Type: {0}".format(content_type))

        # Call next() to start the parser executing.
        parser.next()

        # Return our parser.
        return parser

