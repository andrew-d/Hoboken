from __future__ import with_statement, absolute_import, print_function

from hoboken.objects.http import quote, unquote
from hoboken.objects.util import cached_property, iter_close
from hoboken.six import (
    binary_type,
    text_type,
    iteritems,
    Iterator,
    with_metaclass,
    advance_iterator,
    PY3,
)

try:
    from urlparse import parse_qs
except ImportError:
    from urllib.parse import parse_qs

import re
from io import BytesIO
from functools import wraps
from types import FunctionType
from collections import namedtuple

# States for the querystring parser.
STATE_BEFORE_FIELD = 0
STATE_FIELD_NAME   = 1
STATE_FIELD_DATA   = 2

# States for the multipart parser
STATE_START                     = 0
STATE_START_BOUNDARY            = 1
STATE_HEADER_FIELD_START        = 2
STATE_HEADER_FIELD              = 3
STATE_HEADER_VALUE_START        = 4
STATE_HEADER_VALUE              = 5
STATE_HEADER_VALUE_ALMOST_DONE  = 6
STATE_HEADERS_ALMOST_DONE       = 7
STATE_PART_DATA_START           = 8
STATE_PART_DATA                 = 9
STATE_PART_DATA_END             = 10
STATE_END                       = 11

# Flags for the multipart parser.
FLAG_PART_BOUNDARY              = 1
FLAG_LAST_BOUNDARY              = 2

# Get constants.  Since iterating over a str on Python 2 gives you a 1-length
# string, but iterating over a bytes object on Python 3 gives you an integer,
# we need to save these constants.
CR = b'\r'[0]
LF = b'\n'[0]
COLON = b':'[0]
HYPHEN = b'-'[0]
SPACE = b' '[0]
AMPERSAND = b'&'[0]
SEMICOLON = b';'[0]
LOWER_A = b'a'[0]
LOWER_Z = b'z'[0]

# Lower-casing a character is different, because of the difference between
# str on Py2, and bytes on Py3.  Same with getting the ordinal value of a byte
# These functions abstract that.
if PY3:
    lower_char = lambda c: c | 0x20
    ord_char = lambda c: c
else:
    lower_char = lambda c: c.lower()
    ord_char = lambda c: ord(c)


# These are regexes for parsing header values.
SPECIAL_CHARS = re.escape(b'()<>@,;:\\"/[]?={} \t')
QUOTED_STR = br'"(?:\\.|[^"])*"'
VALUE_STR = br'(?:[^%s]+|%s)' % (SPECIAL_CHARS, QUOTED_STR)
OPTION_RE_STR = br'(?:;|^)\s*([^%s]+)\s*=\s*(%s)' % (SPECIAL_CHARS, VALUE_STR)
OPTION_RE = re.compile(OPTION_RE_STR)


class FormParserError(ValueError):
    pass


def parse_content_type(value):
    """
    Parses a Content-Type header into a value in the following format:
        (content_type, {parameters})
    """
    if not value:
        return (b'', {})

    # If we have no options, return the string as-is.
    if b';' not in value:
        return (value.lower().strip(), {})

    # Split at the first semicolon, to get our value and then options.
    ctype, rest = value.split(b';', 1)
    options = {}

    # Parse the options.
    for match in OPTION_RE.finditer(rest):
        key = match.group(1).lower()
        value = match.group(2)
        if value[0] == '"' and value[-1] == '"':
            # Unquote the value.
            value = value[1:-1]
            value = value.replace('\\\\', '\\').replace('\\"', '"')

        # If the value is a filename, we need to fix a bug on IE6 that sends
        # the full file path instead of the filename.
        if key == 'filename':
            if value[1:3] == ':\\' or value[:2] == '\\\\':
                value = value.split('\\')[-1]

        options[key] = value

    return ctype, options


# Simple container for a (field_name, value) tuple.
Field = namedtuple('Field', ['name', 'value'])


# TODO: Fill this in with required stuff
class File(object):
    """
    This class represents an uploaded file.
    """
    def __init__(self, filename, mime=None):
        self.filename = filename
        self.mime = mime or 'application/octet-stream'
        self.fileobj = BytesIO()

    def close(self):
        self.fileobj.close()


class MultipartPart(object):
    """
    This class encapsulates a portion of a multipart message.
    """
    def __init__(self):
        self.headers = {}

    def add_header(self, header, val):
        self.headers[header] = val

    @property
    def content_type(self):
        # TODO: If we don't have one, what do we assume?
        return self.headers.get('Content-Type')

    @property
    def file_name(self):
        # TODO: parse content-disposition header
        pass

    @property
    def transfer_encoding(self):
        # TODO: according to RFC1341, the default is 7bit.  Check for HTTP?
        return self.headers.get('Content-Transfer-Encoding', 'binary')


class BaseParser(object):
    """
    This class implements some helpful methods for parsers.  Currently, it
    implements the callback logic in a central location.
    """
    def callback(self, name, data=None, start=None, end=None):
        """
        This function calls a provided callback with some data.
        """
        func = self.callbacks.get("on_" + name)
        if func is None:
            return

        # Depending on whether we're given a buffer...
        if data is not None:
            # Don't do anything if we have start == end.
            if start is not None and start == end:
                return

            # print("Calling %s with data[%d:%d] = %r" % ('on_' + name, start, end, data[start:end]))
            func(data, start, end)
        else:
            # print("Calling %s with no data" % ('on_' + name,))
            func()

    def set_callback(self, name, new_func):
        """
        Update the function for a callback.  Removes from the callbacks dict
        if new_func is None.
        """
        if new_func is None:
            self.callbacks.pop(name, None)
        else:
            self.callbacks[name] = new_func



class OctetStreamParser(BaseParser):
    """
    This parser parses an octet-stream request body and calls callbacks when
    incoming data is received.  Callbacks are:
        - on_start
        - on_data       (with data parameters)
        - on_end
    """
    def __init__(self, callbacks={}):
        self.callbacks = callbacks

        self._started = False

    def write(self, data):
        if not self._started:
            self.callback('start')
            self._started = True

        # Emit an end callback if we're done.
        if len(data) == 0:
            self.callback('end')
            return 0

        # Just emit the data callback as-is.
        self.callback('data', data, 0, len(data))


class QuerystringParser(BaseParser):
    """
    This is a streaming querystring parser.  It will consume data, and call
    the callbacks given when it has enough data.

    Valid callbacks (* means with data):
        - on_field_start
        - on_field_name         *
        - on_field_data         *
        - on_field_end
    """
    SPLIT_RE = re.compile(b'[&;]')

    def __init__(self, callbacks={}, keep_blank_values=False,
                 strict_parsing=False, max_size=-1):
        self.state = STATE_BEFORE_FIELD

        self.callbacks = callbacks
        self.max_size = max_size

        # TODO: these currently don't do anything.  We should make them behave
        # like expected.
        self.keep_blank_values = keep_blank_values
        self.strict_parsing = strict_parsing

    def write(self, data):
        state = self.state

        # If we're called with an empty data string, we treat it as the end, in
        # which case we might need to emit an "end" callback.
        if len(data) == 0:
            if state == STATE_FIELD_DATA:
                self.callback('field_end')
            return 0

        i = 0
        while i < len(data):
            ch = data[i]

            # Depending on our state...
            if state == STATE_BEFORE_FIELD:
                # Skip leading seperators.
                # TODO: skip multiple ampersand chunks? e.g. "foo=bar&&&a=b"?
                if ch == AMPERSAND or ch == SEMICOLON:
                    pass
                else:
                    # Emit a field-start event, and go to that state.
                    self.callback('field_start')
                    i -= 1
                    state = STATE_FIELD_NAME

            elif state == STATE_FIELD_NAME:
                # See if we can find an equals sign in the remaining data.  If
                # so, we can immedately emit the field name and jump to the
                # data state.
                equals_pos = data.find(b'=', i)
                if equals_pos != -1:
                    # Emit this name.
                    self.callback('field_name', data, i, equals_pos)

                    # Jump i to this position.  Note that it will then have 1
                    # added to it below, which means the next iteration of this
                    # loop will inspect the character after the equals sign.
                    i = equals_pos
                    state = STATE_FIELD_DATA
                else:
                    # No equals sign found.  Just emit the rest as a name.
                    self.callback('field_name', data, i, len(data))
                    i = len(data)

            elif state == STATE_FIELD_DATA:
                # Try finding either an ampersand or a semicolon after this
                # position.
                sep_pos = data.find(b'&', i)
                if sep_pos == -1:
                    sep_pos = data.find(b';', i)

                # If we found it, callback this bit as data and then go back
                # to expecting to find a field.
                if sep_pos != -1:
                    self.callback('field_data', data, i, sep_pos)
                    self.callback('field_end')

                    # Note that we go to the seperator, which brings us to the
                    # "before field" state.  This allows us to properly emit
                    # "field_start" events only when we actually have data for
                    # a field of some sort.
                    i = sep_pos - 1
                    state = STATE_BEFORE_FIELD

                # Otherwise, emit the rest as data and finish.
                else:
                    self.callback('field_data', data, i, len(data))
                    i = len(data)

            else:
                return i

            i += 1

        self.state = state


class MultipartParser(BaseParser):
    """
    This class implements a state machine that parses a multipart/form-data
    message.

    Valid callbacks (* indicates given data):
        - on_part_begin
        - on_part_data              *
        - on_part_end
        - on_header_begin
        - on_header_field           *
        - on_header_value           *
        - on_header_end
        - on_headers_finished
        - on_end
    """

    def __init__(self, boundary, callbacks={}):
        # Initialize parser state.
        self.state = STATE_START
        self.index = self.flags = 0

        # Save callbacks.
        self.callbacks = callbacks

        # Setup marks.  These are used to track the state of data recieved.
        self.marks = {}

        # # Precompute the skip table for the Boyer-Moore-Horspool algorithm.
        # skip = [len(boundary) for x in range(256)]
        # for i in range(len(boundary) - 1):
        #     skip[ord_char(boundary[i])] = len(boundary) - i - 1

        # # We use a tuple since it's a constant, and marginally faster.
        # self.skip = tuple(skip)

        # Save our boundary.
        self.boundary = b'\r\n--' + boundary

        # Get a set of characters that belong to our boundary.
        self.boundary_chars = set(boundary)

        # We also create a lookbehind list.
        # TODO: why +8?
        self.lookbehind = [0 for x in range(len(boundary) + 8)]

    def write(self, data):
        # Get values from locals.
        boundary = self.boundary

        # Get our state, flags and index.  These are persisted between calls to
        # this function.
        state = self.state
        index = self.index
        flags = self.flags

        # Our index defaults to 0.
        i = 0

        # Get a mark.
        def get_mark(name):
            return self.marks.get(name)

        # Set a mark.
        def set_mark(name):
            self.marks[name] = i

        # Remove a mark.
        def delete_mark(name, reset=False):
            self.marks.pop(name, None)

        # Helper function that makes calling a callback with data easier. The
        # 'remaining' parameter will callback from the marked value until the
        # end of the buffer, and reset the mark, instead of deleting it.  This
        # is used at the end of the function to call our callbacks with any
        # remaining data in this chunk.
        def data_callback(name, remaining=False):
            marked_index = self.marks.get(name)
            if marked_index is None:
                return

            # If we're getting remaining data, we ignore the current i value
            # and just call with the remaining data.
            if remaining:
                self.callback(name, data, marked_index, len(data))
                self.marks[name] = 0

            # Otherwise, we call it from the mark to the current byte we're
            # processing.
            else:
                self.callback(name, data, marked_index, i)
                self.marks.pop(name, None)

        # For each byte...
        while i < len(data):
            # Get our current character and increment the index.
            c = data[i]

            if state == STATE_START:
                # Skip leading newlines
                if c == CR or c == LF:
                    i += 1
                    continue

                # index is used as in index into our boundary.  Set to 0.
                index = 0

                # Move to the next state, but decrement i so that we re-process
                # this character.
                state = STATE_START_BOUNDARY
                i -= 1

            elif state == STATE_START_BOUNDARY:
                # Check to ensure that the last 2 characters in our boundary
                # are CRLF.
                if index == len(boundary) - 2:
                    if c != CR:
                        # Error!
                        return i

                    index += 1

                elif index == len(boundary) - 2 + 1:
                    if c != LF:
                        return i

                    # The index is now used for XXX FILL ME IN XXX
                    index = 0

                    # Callback for the start of a part.
                    self.callback('part_begin')

                    # Move to the next character and state.
                    state = STATE_HEADER_FIELD_START

                else:
                    # Check to ensure our boundary matches
                    if c != boundary[index + 2]:
                        # print('start_boundary: expected %r, found %r' % (c, boundary[index + 2]))
                        return i

                    # Increment index into boundary and continue.
                    index += 1

            elif state == STATE_HEADER_FIELD_START:
                # Mark the start of a header field here, reset the index, and
                # continue parsing our header field.
                index = 0

                # Set a mark of our header field.
                set_mark('header_field')

                # Move to parsing header fields.
                state = STATE_HEADER_FIELD
                i -= 1

            elif state == STATE_HEADER_FIELD:
                # If we've reached a CR at the beginning of a header, it means
                # that we've reached the second of 2 newlines, and so there are
                # no more headers to parse.
                if c == CR:
                    delete_mark('header_field')
                    state = STATE_HEADERS_ALMOST_DONE
                    i += 1
                    continue

                # Increment our index in the header.
                index += 1

                # Do nothing if we encounter a hyphen.
                if c == HYPHEN:
                    pass

                # If we've reached a colon, we're done with this header.
                elif c == COLON:
                    # A 0-length header is an error.
                    if index == 1:
                        # print('header_field: found 0-length header')
                        return i

                    # Call our callback with the header field.
                    data_callback('header_field')

                    # Move to parsing the header value.
                    state = STATE_HEADER_VALUE_START

                else:
                    # Lower-case this character, and ensure that it is in fact a
                    # valid letter.  If not, it's an error.
                    cl = lower_char(c)
                    if cl < LOWER_A or cl > LOWER_Z:
                        # print('header_field: found non-alpha character %r' % (c,))
                        return i

            elif state == STATE_HEADER_VALUE_START:
                # Skip leading spaces.
                if c == SPACE:
                    i += 1
                    continue

                # Mark the start of the header value.
                set_mark('header_value')

                # Move to the header-value state, reprocessing this character.
                state = STATE_HEADER_VALUE
                i -= 1

            elif state == STATE_HEADER_VALUE:
                # If we've got a CR, we're nearly done our headers.  Otherwise,
                # we do nothing and just move past this character.
                if c == CR:
                    data_callback('header_value')
                    self.callback('header_end')
                    state == STATE_HEADER_VALUE_ALMOST_DONE

            elif state == STATE_HEADER_VALUE_ALMOST_DONE:
                # The last character should be a LF.  If not, it's an error.
                if c != LF:
                    return i

                # Move back to the start of another header.  Note that if that
                # state detects ANOTHER newline, it'll trigger the end of our
                # headers.
                state = STATE_HEADER_FIELD_START

            elif state == STATE_HEADERS_ALMOST_DONE:
                # We're almost done our headers.  This is reached when we parse
                # a CR at the beginning of a header, so our next character
                # should be a LF, or it's an error.
                if c != LF:
                    return i

                self.callback('headers_finished')
                state = STATE_PART_DATA_START

            elif state == STATE_PART_DATA_START:
                # Mark the start of our part data.
                mark('part_data')

                # Start processing part data, including this character.
                state = STATE_PART_DATA
                i -= 1

            elif state == STATE_PART_DATA:
                # We're processing our part data right now.  During this, we
                # need to efficiently search for our boundary, since any data
                # on any number of lines can be a part of the current data.
                # We use the Boyer-Moore-Horspool algorithm to efficiently
                # search through the remainder of the buffer looking for our
                # boundary.

                # Save the current value of our index.  We use this in case we
                # find part of a boundary, but it doesn't match fully
                prev_index = index

                # Set up variables.
                boundary_length = len(boundary)
                boundary_end = boundary_length - 1
                data_length = len(data)
                boundary_chars = self.boundary_chars

                # If our index is 0, we're starting a new part, so start our
                # search.
                if index == 0:
                    # Search forward until we either hit the end of our buffer,
                    # or reach a character that's in our boundary.
                    i += boundary_end
                    while i < data_length and data[i] not in boundary_chars:
                        i += boundary_length

                    # Reset i back the length of our boundary, which is the
                    # earliest possible location that could be our match (i.e.
                    # if we've just broken out of our loop since we saw the
                    # last character in our boundary)
                    i -= boundary_end
                    c = data[i]

                # Now, we have a couple of cases here.  If our index is before
                # the end of the boundary...
                if index < boundary_length:
                    # If the character matches...
                    if boundary[index] == c:
                        if index == 0:
                            data_callback('part_data')
                            pass

                        # The current character matches, so continue!
                        index += 1
                    else:
                        index = 0

                # Our index is equal to the length of our boundary!
                elif index == boundary_length:
                    # First we increment it.
                    index += 1

                    # Now, if we've reached a newline, we need to set this as
                    # the potential end of our boundary.
                    if c == CR:
                        flags |= FLAG_PART_BOUNDARY

                    # Otherwise, if this is a hyphen, we might be at the last
                    # of all boundaries.
                    elif c == HYPHEN:
                        flags |= FLAG_LAST_BOUNDARY

                    # Otherwise, we reset our index, since this isn't either a
                    # newline or a hyphen.
                    else:
                        index = 0

                # Our index is right after the part boundary, which should be
                # a LF.
                elif index == boundary_length + 1:
                    # If we're at a part boundary (i.e. we've seen a CR
                    # character already)...
                    if flags & FLAG_PART_BOUNDARY:
                        # We need a LF character next.
                        if c == LF:
                            # Unset the part boundary flag.
                            flags &= (~FLAG_PART_BOUNDARY)

                            # Callback indicating that we've reached the end of
                            # a part, and are starting a new one.
                            self.callback('part_end')
                            self.callback('part_begin')

                            # Move to parsing new headers.
                            index = 0
                            state = STATE_HEADER_FIELD_START
                            i += 1
                            continue

                        # We didn't find an LF character, so no match.  Reset
                        # our index.
                        index = 0

                    # Otherwise, if we're at the last boundary (i.e. we've
                    # seen a hyphen already)...
                    elif flags & FLAG_LAST_BOUNDARY:
                        # We need a second hyphen here.
                        if c == HYPHEN:
                            # Callback to end the current part, and then the
                            # mesaage.
                            self.callback('part_end')
                            self.callback('end')
                            state = STATE_END
                        else:
                            # No match, so reset index.
                            index = 0

                    # No other flags, which mean we've got no match.  Reset
                    # our index.
                    else:
                        index = 0

                # If we have an index, we need to keep this byte for later, in
                # case we can't match the full boundary.
                if index > 0:
                    self.lookbehind[index - 1] = c

                # Otherwise, our index is 0.  If the previous index is not, it
                # means we reset something, and we need to take the data we
                # thought was part of our boundary and send it along as actual
                # data.
                elif prev_index > 0:
                    # Callback to write the saved data.
                    self.callback('part_data', self.lookbehind, 0, prev_index)

                    # Overwrite our previous index.
                    prev_index = 0

                    # Re-set our mark for part data.
                    mark('part_data')

                    # Re-consider the current character, since this could be
                    # the start of the boundary itself.
                    i -= 1

            elif state == STATE_END:
                # Do nothing and just consume a byte in the end state.
                pass

            else:
                # We got into a strange state somehow!  Just stop processing.
                print('ERROR: in a strange state!')
                return i

            # Move to the next byte.
            i += 1

        # We call our callbacks with any remaining data.  Note that we pass
        # the 'remaining' flag, which sets the mark back to 0 instead of
        # deleting it, if it's found.  This is because, if the mark is found
        # at this point, we assume that there's data for one of these things
        # that has been parsed, but not yet emitted.  And, as such, it implies
        # that we haven't yet reached the end of this 'thing'.  So, by setting
        # the mark to 0, we cause any data callbacks that take place in future
        # calls to this function to start from the beginning of that buffer.
        data_callback('header_field', True)
        data_callback('header_value', True)
        data_callback('part_data', True)

        # Save values to locals.
        self.state = state
        self.index = index
        self.flags = flags

        # Return our data length to indicate no errors, and that we processed
        # all of it.
        return len(data)


class FormParser(object):
    # This is the default configuration for our form parser.
    DEFAULT_CONFIG = {
        'MAX_FIELD_SIZE': 1024,
        'MAX_QUERYSTRING_SIZE': 2 * 1024,       # 2 * max field size, since it
                                                # contains the name and value
        'MAX_FILE_SIZE': 10 * 1024 * 1024,
    }

    def __init__(self, content_type, boundary=None, content_length=-1,
                 file_name=None, charset='latin-1', config={}):
        self.content_length = content_length
        self.boundary = boundary
        self.charset = charset
        self.bytes_received = 0

        # Set configuration options.
        self.config = self.DEFAULT_CONFIG.copy()
        self.config.update(config)

        # Depending on the Content-Type, we instantiate the correct parser.
        if content_type == 'application/octet-stream':
            # Instantiate an octet-stream parser
            parser = OctetStreamParser(file_name or '', content_type)

        elif (content_type == 'application/x-www-form-urlencoded' or
              content_type == 'application/x-url-encoded'):

            name_buffer = []
            data_buffer = []

            def on_field_start():
                pass

            def on_field_name(data, start, end):
                name_buffer.append(data[start:end])

            def on_field_data(data, start, end):
                data_buffer.append(data[start:end])

            def on_field_end():
                f = Field(
                    name=b''.join(name_buffer),
                    value=b''.join(data_buffer)
                )

                self.onField(f)

                del name_buffer[:]
                del data_buffer[:]

            # Setup callbacks.
            callbacks = {
                'on_field_start': on_field_start,
                'on_field_name': on_field_name,
                'on_field_data': on_field_data,
                'on_field_end': on_field_end,
            }

            # Instantiate parser.
            parser = QuerystringParser(
                        callbacks=callbacks,
                        max_size=self.config['MAX_QUERYSTRING_SIZE']
                     )

        elif content_type == 'multipart/form-data':
            if boundary is None:
                raise FormParserError("No boundary given")

            part = None
            header_name = []
            header_value = []

            def on_part_begin():
                part = MultipartPart()

            def on_part_data(data, start, end):
                pass

            def on_part_end():
                pass

            def on_header_field(data, start, end):
                header_name.append(data[start:end])

            def on_header_value(data, start, end):
                header_value.append(data[start:end])

            def on_header_end():
                part.add_header(b''.join(header_name), b''.join(header_value))
                del header_name[:]
                del header_value[:]

            def on_headers_finished():
                # Parse the given Content-Transfer-Encoding to determine what
                # we need to do with the incoming data.
                if part.transfer_encoding == 'binary':
                    pass

                elif part.transfer_encoding == 'base64':
                    pass

                else:
                    # TODO: do we really want to raise an exception here?  Or
                    # should we just continue parsing?
                    raise FormParserError(
                        'Unknown Content-Transfer-Encoding "{0}"'.format(
                            part.transfer_encoding
                        )
                    )

            def on_end(self):
                pass

            # These are our callbacks for the parser.
            callbacks = {
                'on_part_begin': on_part_begin,
                'on_part_data': on_part_data,
                'on_part_end': on_part_end,
                'on_header_field': on_header_field,
                'on_header_value': on_header_value,
                'on_header_end': on_header_end,
                'on_headers_finished': on_headers_finished,
                'on_end': on_end,
            }

            # Instantiate a multipart parser.
            parser = MultipartParser(boundary, callbacks)

        else:
            raise FormParserError("Unknown Content-Type: {0}".format(content_type))

        self.parser = parser

    def write(self, data):
        self.bytes_received += len(data)
        # TODO: check the parser's return value for errors?
        return self.parser.write(data)

    def onField(self, field):
        """
        This function is called whenever we have a new form field.
        """
        pass

    def handlePart(self, part):
        """
        This function gets called whenever we get a new request part.  The
        'part' argument will be an instance of MultipartPart().
        """
        pass


class RequestBodyMixin(object):
    def __init__(self, *args, **kwargs):
        super(RequestBodyMixin, self).__init__(*args, **kwargs)

        self.__form_config = {}

        # If we have a config object...
        if hasattr(self, 'config'):
            # For each option, see if it's set in our config.
            # NOTE: We can't simply use '.update', since we have some non-form
            # config values in the dictionary.
            for f in FormParser.DEFAULT_CONFIG.keys():
                val = self.config.get(f)
                if val is not None:
                    self.__form_config[f] = val

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
    # Parts:
    #   - Mixin:
    #       - Reads the content-length and boundary to give to the parser
    #       - Has the option of feeding the body iterator to the parser
    #       - Can encapsulate the parser to parse into 'form' and 'files'
    #   - Form parser:
    #       - Depending on the type of the underlying content-type, will pick
    #         the correct parser (multipart, form-data, octet-stream, ???)
    #   - Typed parser:
    #       - Responsible for parsing a specific type of request body.
    #   - Field:
    #       - Container for field-name/field-value
    #   - File:
    #       - Container for field-name/file-name/file-data.
    #       - File data can be stored in memory, or on disk
    #       - Can have a size/memory limit.
    #       - Should just be a file-like object + attributes
    #
    # Control flow:
    #   - Mixin obtains content-type, content-length, and boundary, and
    #     instantiates a form parser instance
    #   - Form parser will, depending on the content-type, create the correct
    #     underlying parser.
    #   - Form parser waits for data, writes data into underlying parser.
    #   - Underlying parser calls on_part, on_part_start, on_part_data,
    #     on_part_end, etc. callbacks with appropriate values.
    #   - Default callbacks are into the form parser, which will simply write
    #     the data into our file, or save a field.
    #   - Form parser has callbacks on_field and on_file, which are called when
    #     we have a field/file that is finished.

    # TODO: do we make this a property?
    def form_parser(self):
        # Before we do anything else, we need to parse our Content-Type and
        # Content-Length headers.
        content_length = int(self.headers.get('Content-Length', -1))
        content_type = self.headers.get('Content-Type')
        if content_type is None:
            raise ValueError("No Content-Type header given!")

        # Try and get our boundary.
        content_type, params = parse_content_type(content_type)
        boundary = params.get('boundary')

        # Try and get a filename.
        file_name = self.headers.get('X-File-Name')

        # Instantiate a form parser.
        form_parser = FormParser(content_type,
                                 boundary=boundary,
                                 content_length=content_length,
                                 file_name=file_name,
                                 config=self.__form_config)

        # TODO: feed the parser data somehow

        # Return our parser.
        return form_parser

    def parse_body(self):
        # Get a form parser.
        fp = self.form_parser()
        fields = {}
        files = {}

        # For each field/file.
        for type, data in fp:
            if type == 'field':
                fields[data.name] = data
            elif type == 'file':
                files[data.name] = data
            else:
                pass

        # TODO: set these somewhere?
        #self._fields = fields
        #self._files = files

