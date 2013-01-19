# -*- coding: utf-8 -*-

import os
import sys
import glob
import yaml
import base64
import tempfile
from hoboken.tests.compat import parametrize, parametrize_class, unittest
from io import BytesIO

from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.request_body import *
from hoboken.six import binary_type, text_type


# Get the current directory for our later test cases.
curr_dir = os.path.abspath(os.path.dirname(__file__))


def force_bytes(val):
    if isinstance(val, text_type):
        val = val.encode(sys.getfilesystemencoding())

    return val


class TestField(unittest.TestCase):
    def setUp(self):
        self.f = Field(b'foo')

    def test_name(self):
        self.assertEqual(self.f.field_name, b'foo')

    def test_data(self):
        self.f.write(b'test123')
        self.assertEqual(self.f.value, b'test123')

    def test_cache_expiration(self):
        self.f.write(b'test')
        self.assertEqual(self.f.value, b'test')
        self.f.write(b'123')
        self.assertEqual(self.f.value, b'test123')

    def test_finalize(self):
        self.f.write(b'test123')
        self.f.finalize()
        self.assertEqual(self.f.value, b'test123')

    def test_close(self):
        self.f.write(b'test123')
        self.f.close()
        self.assertEqual(self.f.value, b'test123')

    def test_from_value(self):
        f = Field.from_value(b'name', b'value')
        self.assertEqual(f.field_name, b'name')
        self.assertEqual(f.value, b'value')

    def test_equality(self):
        f1 = Field.from_value(b'name', b'value')
        f2 = Field.from_value(b'name', b'value')

        self.assertEqual(f1, f2)

    def test_equality_with_other(self):
        f = Field.from_value(b'foo', b'bar')
        self.assertFalse(f == b'foo')
        self.assertFalse(b'foo' == f)


class TestFile(unittest.TestCase):
    def setUp(self):
        self.c = {}
        self.d = force_bytes(tempfile.mkdtemp())
        self.f = File(b'foo.txt', config=self.c)

    def assert_data(self, data):
        f = self.f.file_object
        f.seek(0)
        self.assertEqual(f.read(), data)
        f.seek(0)
        f.truncate()

    def assert_exists(self):
        full_path = os.path.join(self.d, self.f.actual_file_name)
        self.assertTrue(os.path.exists(full_path))

    def test_simple(self):
        self.f.write(b'foobar')
        self.assert_data(b'foobar')

    def test_invalid_write(self):
        m = Mock()
        m.write.return_value = 5
        self.f._fileobj = m
        v = self.f.write(b'foobar')
        self.assertEqual(v, 5)

    def test_file_fallback(self):
        self.c['MAX_MEMORY_FILE_SIZE'] = 1

        self.f.write(b'1')
        self.assertTrue(self.f.in_memory)
        self.assert_data(b'1')

        self.f.write(b'123')
        self.assertFalse(self.f.in_memory)
        self.assert_data(b'123')

        # Test flushing too.
        old_obj = self.f.file_object
        self.f.flush_to_disk()
        self.assertFalse(self.f.in_memory)
        self.assertIs(self.f.file_object, old_obj)

    def test_file_fallback_with_data(self):
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        self.f.write(b'1' * 10)
        self.assertTrue(self.f.in_memory)

        self.f.write(b'2' * 10)
        self.assertFalse(self.f.in_memory)

        self.assert_data(b'11111111112222222222')

    def test_file_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = self.d
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assertFalse(self.f.in_memory)

        # Assert that the file exists
        self.assertIsNotNone(self.f.actual_file_name)
        self.assert_exists()

    def test_file_full_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assertFalse(self.f.in_memory)

        # Assert that the file exists
        self.assertEqual(self.f.actual_file_name, b'foo')
        self.assert_exists()

    def test_file_full_name_with_ext(self):
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assertFalse(self.f.in_memory)

        # Assert that the file exists
        self.assertEqual(self.f.actual_file_name, b'foo.txt')
        self.assert_exists()

    def test_file_full_name_with_ext(self):
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assertFalse(self.f.in_memory)

        # Assert that the file exists
        self.assertEqual(self.f.actual_file_name, b'foo.txt')
        self.assert_exists()

    def test_no_dir_with_extension(self):
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assertFalse(self.f.in_memory)

        # Assert that the file exists
        ext = os.path.splitext(self.f.actual_file_name)[1]
        self.assertEqual(ext, b'.txt')
        self.assert_exists()

    def test_invalid_dir_with_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = force_bytes(os.path.join('/', 'tmp', 'notexisting'))
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 5

        # Write.
        with self.assertRaises(FileError):
            self.f.write(b'1234567890')

    def test_invalid_dir_no_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = force_bytes(os.path.join('/', 'tmp', 'notexisting'))
        self.c['UPLOAD_KEEP_FILENAME'] = False
        self.c['MAX_MEMORY_FILE_SIZE'] = 5

        # Write.
        with self.assertRaises(FileError):
            self.f.write(b'1234567890')

    # TODO: test uploading two files with the same name.


class TestParseOptionsHeader(unittest.TestCase):
    def test_simple(self):
        t, p = parse_options_header(b'application/json')
        self.assertEqual(t, b'application/json')
        self.assertEqual(p, {})

    def test_blank(self):
        t, p = parse_options_header(b'')
        self.assertEqual(t, b'')
        self.assertEqual(p, {})

    def test_single_param(self):
        t, p = parse_options_header(b'application/json;par=val')
        self.assertEqual(t, b'application/json')
        self.assertEqual(p, {b'par': b'val'})

    def test_single_param_with_spaces(self):
        t, p = parse_options_header(b'application/json;     par=val')
        self.assertEqual(t, b'application/json')
        self.assertEqual(p, {b'par': b'val'})

    def test_multiple_params(self):
        t, p = parse_options_header(b'application/json;par=val;asdf=foo')
        self.assertEqual(t, b'application/json')
        self.assertEqual(p, {b'par': b'val', b'asdf': b'foo'})

    def test_quoted_param(self):
        t, p = parse_options_header(b'application/json;param="quoted"')
        self.assertEqual(t, b'application/json')
        self.assertEqual(p, {b'param': b'quoted'})

    def test_quoted_param_with_semicolon(self):
        t, p = parse_options_header(b'application/json;param="quoted;with;semicolons"')
        self.assertEqual(p[b'param'], b'quoted;with;semicolons')

    def test_quoted_param_with_escapes(self):
        t, p = parse_options_header(b'application/json;param="This \\" is \\" a \\" quote"')
        self.assertEqual(p[b'param'], b'This " is " a " quote')

    def test_handles_ie6_bug(self):
        t, p = parse_options_header(b'text/plain; filename="C:\\this\\is\\a\\path\\file.txt"')

        self.assertEqual(p[b'filename'], b'file.txt')


class TestBaseParser(unittest.TestCase):
    def setUp(self):
        self.b = BaseParser()
        self.b.callbacks = {}

    def test_callbacks(self):
        # The stupid list-ness is to get around lack of nonlocal on py2
        l = [0]
        def on_foo():
            l[0] += 1

        self.b.set_callback('foo', on_foo)
        self.b.callback('foo')
        self.assertEqual(l[0], 1)

        self.b.set_callback('foo', None)
        self.b.callback('foo')
        self.assertEqual(l[0], 1)


class TestQuerystringParser(unittest.TestCase):
    def assert_fields(self, *args, **kwargs):
        if kwargs.pop('finalize', True):
            self.p.finalize()

        self.assertEqual(self.f, list(args))
        if kwargs.get('reset', True):
            self.f = []

    def setUp(self):
        self.f = []

        name_buffer = []
        data_buffer = []

        def on_field_name(data, start, end):
            name_buffer.append(data[start:end])

        def on_field_data(data, start, end):
            data_buffer.append(data[start:end])

        def on_field_end():
            self.f.append((
                b''.join(name_buffer),
                b''.join(data_buffer)
            ))

            del name_buffer[:]
            del data_buffer[:]

        callbacks = {
            'on_field_name': on_field_name,
            'on_field_data': on_field_data,
            'on_field_end': on_field_end
        }

        self.p = QuerystringParser(callbacks)

    def test_simple_querystring(self):
        self.p.write(b'foo=bar')

        self.assert_fields((b'foo', b'bar'))

    def test_querystring_blank_beginning(self):
        self.p.write(b'&foo=bar')

        self.assert_fields((b'foo', b'bar'))

    def test_querystring_blank_end(self):
        self.p.write(b'foo=bar&')

        self.assert_fields((b'foo', b'bar'))

    def test_multiple_querystring(self):
        self.p.write(b'foo=bar&asdf=baz')

        self.assert_fields(
            (b'foo', b'bar'),
            (b'asdf', b'baz')
        )

    def test_streaming_simple(self):
        self.p.write(b'foo=bar&')
        self.assert_fields(
            (b'foo', b'bar'),
            finalize=False
        )

        self.p.write(b'asdf=baz')
        self.assert_fields(
            (b'asdf', b'baz')
        )

    def test_streaming_break(self):
        self.p.write(b'foo=one')
        self.assert_fields(finalize=False)

        self.p.write(b'two')
        self.assert_fields(finalize=False)

        self.p.write(b'three')
        self.assert_fields(finalize=False)

        self.p.write(b'&asd')
        self.assert_fields(
            (b'foo', b'onetwothree'),
            finalize=False
        )

        self.p.write(b'f=baz')
        self.assert_fields(
            (b'asdf', b'baz')
        )

    def test_semicolon_seperator(self):
        self.p.write(b'foo=bar;asdf=baz')

        self.assert_fields(
            (b'foo', b'bar'),
            (b'asdf', b'baz')
        )

    # TODO: test overlarge fields, blank values, and strict parsing


class TestOctetStreamParser(unittest.TestCase):
    def setUp(self):
        self.d = []
        self.started = 0
        self.finished = 0

        def on_start():
            self.started += 1

        def on_data(data, start, end):
            self.d.append(data[start:end])

        def on_end():
            self.finished += 1

        callbacks = {
            'on_start': on_start,
            'on_data': on_data,
            'on_end': on_end
        }

        self.p = OctetStreamParser(callbacks)

    def assert_data(self, data, finalize=True):
        self.assertEqual(b''.join(self.d), data)
        self.d = []

    def assert_started(self, val=True):
        if val:
            self.assertEqual(self.started, 1)
        else:
            self.assertEqual(self.started, 0)

    def assert_finished(self, val=True):
        if val:
            self.assertEqual(self.finished, 1)
        else:
            self.assertEqual(self.finished, 0)

    def test_simple(self):
        # Assert is not started
        self.assert_started(False)

        # Write something, it should then be started + have data
        self.p.write(b'foobar')
        self.assert_started()
        self.assert_data(b'foobar')

        # Finalize, and check
        self.assert_finished(False)
        self.p.finalize()
        self.assert_finished()

    def test_multiple_chunks(self):
        self.p.write(b'foo')
        self.p.write(b'bar')
        self.p.write(b'baz')
        self.p.finalize()

        self.assert_data(b'foobarbaz')
        self.assert_finished()


class TestBase64Decoder(unittest.TestCase):
    # Note: base64('foobar') == 'Zm9vYmFy'
    def setUp(self):
        self.f = BytesIO()
        self.d = Base64Decoder(self.f)

    def assert_data(self, data, finalize=True):
        if finalize:
            self.d.finalize()

        self.f.seek(0)
        self.assertEqual(self.f.read(), data)
        self.f.seek(0)
        self.f.truncate()

    def test_simple(self):
        self.d.write(b'Zm9vYmFy')
        self.assert_data(b'foobar')

    def test_split_properly(self):
        self.d.write(b'Zm9v')
        self.d.write(b'YmFy')
        self.assert_data(b'foobar')

    def test_bad_split(self):
        buff = b'Zm9v'
        for i in range(1, 4):
            first, second = buff[:i], buff[i:]

            self.setUp()
            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foo')

    def test_long_bad_split(self):
        buff = b'Zm9vYmFy'
        for i in range(5, 8):
            first, second = buff[:i], buff[i:]

            self.setUp()
            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foobar')

    def test_close_and_finalize(self):
        parser = Mock()
        f = Base64Decoder(parser)

        f.finalize()
        parser.finalize.assert_called_once_with()

        f.close()
        parser.close.assert_called_once_with()


class TestQuotedPrintableDecoder(unittest.TestCase):
    def setUp(self):
        self.f = BytesIO()
        self.d = QuotedPrintableDecoder(self.f)

    def assert_data(self, data, finalize=True):
        if finalize:
            self.d.finalize()

        self.f.seek(0)
        self.assertEqual(self.f.read(), data)
        self.f.seek(0)
        self.f.truncate()

    def test_simple(self):
        self.d.write(b'foobar')
        self.assert_data(b'foobar')

    def test_with_escape(self):
        self.d.write(b'foo=3Dbar')
        self.assert_data(b'foo=bar')

    def test_with_newline_escape(self):
        self.d.write(b'foo=\r\nbar')
        self.assert_data(b'foobar')

    def test_with_only_newline_escape(self):
        self.d.write(b'foo=\nbar')
        self.assert_data(b'foobar')

    def test_with_split_escape(self):
        self.d.write(b'foo=3')
        self.d.write(b'Dbar')
        self.assert_data(b'foo=bar')

    def test_with_split_newline_escape_1(self):
        self.d.write(b'foo=\r')
        self.d.write(b'\nbar')
        self.assert_data(b'foobar')

    def test_with_split_newline_escape_2(self):
        self.d.write(b'foo=')
        self.d.write(b'\r\nbar')
        self.assert_data(b'foobar')

    def test_close_and_finalize(self):
        parser = Mock()
        f = QuotedPrintableDecoder(parser)

        f.finalize()
        parser.finalize.assert_called_once_with()

        f.close()
        parser.close.assert_called_once_with()


# Load our list of HTTP test cases.
http_tests_dir = os.path.join(curr_dir, 'multipart_tests', 'http')

# Read in all test cases and load them.
http_tests = []
for f in os.listdir(http_tests_dir):
    # Only load the HTTP test cases.
    fname, ext = os.path.splitext(f)
    if ext == '.http':
        # Get the YAML file and load it too.
        yaml_file = os.path.join(http_tests_dir, fname + '.yaml')

        # Load both.
        with open(os.path.join(http_tests_dir, f), 'rb') as f:
            test_data = f.read()

        with open(yaml_file, 'rb') as f:
            yaml_data = yaml.load(f)

        http_tests.append({
            'name': fname,
            'test': test_data,
            'result': yaml_data
        })


def split_all(val):
    """
    This function will split an array all possible ways.  For example:
        split_all([1,2,3,4])
    will give:
        ([1], [2,3,4]), ([1,2], [3,4]), ([1,2,3], [4])
    """
    for i in range(1, len(val) - 1):
        yield (val[:i], val[i:])


@parametrize_class
class TestFormParser(unittest.TestCase):
    def make(self, boundary):
        self.ended = False
        self.files = []
        self.fields = []

        def on_field(f):
            self.fields.append(f)

        def on_file(f):
            self.files.append(f)

        def on_end():
            self.ended = True

        # Get a form-parser instance.
        self.f = FormParser(b'multipart/form-data', on_field, on_file, on_end, boundary=boundary)

    def assert_file_data(self, f, data):
        o = f.file_object
        o.seek(0)
        file_data = o.read()
        self.assertEqual(file_data, data)

    def assert_file(self, field_name, file_name, data):
        # Find this file.
        found = None
        for f in self.files:
            if f.field_name == field_name:
                found = f
                break

        # Assert that we found it.
        self.assertIsNotNone(found)

        try:
            # Assert about this file.
            self.assert_file_data(found, data)
            self.assertEqual(found.file_name, file_name)

            # Remove it from our list.
            self.files.remove(found)
        finally:
            # Close our file
            found.close()

    def assert_field(self, name, value):
        # Find this field in our fields list.
        found = None
        for f in self.fields:
            if f.field_name == name:
                found = f
                break

        # Assert that it exists and matches.
        self.assertIsNotNone(found)
        self.assertEqual(value, found.value)

        # Remove it for future iterations.
        self.fields.remove(found)

    @parametrize('param', http_tests)
    def test_http(self, param):
        # Firstly, create our parser with the given boundary.
        boundary = param['result']['boundary']
        if isinstance(boundary, text_type):
            boundary = boundary.encode('latin-1')
        self.make(boundary)

        # Now, we feed the parser with data.
        processed = self.f.write(param['test'])
        self.f.finalize()

        # print(repr(param))
        # print("")
        # print(repr(self.fields))
        # print(repr(self.files))

        # Do we expect an error?
        if 'error' in param['result']['expected']:
            self.assertEqual(param['result']['expected']['error'], processed)
            return

        # No error!
        self.assertEqual(processed, len(param['test']))

        # Assert that the parser gave us the appropriate fields/files.
        for e in param['result']['expected']:
            # Get our type and name.
            type = e['type']
            name = e['name'].encode('latin-1')

            if type == 'field':
                self.assert_field(name, e['data'])

            elif type == 'file':
                self.assert_file(
                    name,
                    e['file_name'].encode('latin-1'),
                    e['data']
                )

            else:
                assert False

    def test_random_splitting(self):
        """
        This test runs a simple multipart body with one field and one file through every possible split.
        """
        # Load test data.
        test_file = 'single_field_single_file.http'
        with open(os.path.join(http_tests_dir, test_file), 'rb') as f:
            test_data = f.read()

        # We split the file through all cases.
        for first, last in split_all(test_data):
            # Create form parser.
            self.make(b'boundary')

            # Feed with data in 2 chunks.
            i = 0
            i += self.f.write(first)
            i += self.f.write(last)
            self.f.finalize()

            # Assert we processed everything.
            self.assertEqual(i, len(test_data))

            # Assert that our file and field are here.
            self.assert_field(b'field', b'test1')
            self.assert_file(b'file', b'file.txt', b'test2')

    def test_feed_single_bytes(self):
        """
        This test parses a simple multipart body 1 byte at a time.
        """
        # Load test data.
        test_file = 'single_field_single_file.http'
        with open(os.path.join(http_tests_dir, test_file), 'rb') as f:
            test_data = f.read()

        # Create form parser.
        self.make(b'boundary')

        # Write all bytes.
        # NOTE: Can't simply do `for b in test_data`, since that gives
        # an integer when iterating over a bytes object on Python 3.
        i = 0
        for x in range(len(test_data)):
            b = test_data[x:x + 1]
            i += self.f.write(b)

        self.f.finalize()

        # Assert we processed everything.
        self.assertEqual(i, len(test_data))

        # Assert that our file and field are here.
        self.assert_field(b'field', b'test1')
        self.assert_file(b'file', b'file.txt', b'test2')

    def test_bad_start_boundary(self):
        self.make(b'boundary')
        data = b'--boundary\rfoobar'
        i = self.f.write(data)
        self.assertNotEqual(i, len(data))

        self.make(b'boundary')
        data = b'--boundaryfoobar'
        i = self.f.write(data)
        self.assertNotEqual(i, len(data))

    def test_octet_stream(self):
        files = []
        def on_file(f):
            files.append(f)
        on_field = Mock()
        on_end = Mock()

        f = FormParser(b'application/octet-stream', on_field, on_file, on_end=on_end, file_name=b'foo.txt')
        self.assertTrue(isinstance(f.parser, OctetStreamParser))

        f.write(b'test')
        f.write(b'1234')
        f.finalize()

        # Assert that we only recieved a single file, with the right data, and that we're done.
        self.assertFalse(on_field.called)
        self.assertEqual(len(files), 1)
        self.assert_file_data(files[0], b'test1234')
        self.assertTrue(on_end.called)

    def test_querystring(self):
        fields = []
        def on_field(f):
            fields.append(f)
        on_file = Mock()
        on_end = Mock()

        def simple_test(f):
            # Reset tracking.
            del fields[:]
            on_file.reset_mock()
            on_end.reset_mock()

            # Write test data.
            f.write(b'foo=bar')
            f.write(b'&test=asdf')
            f.finalize()

            # Assert we only recieved 2 fields...
            self.assertFalse(on_file.called)
            self.assertEqual(len(fields), 2)

            # ...assert that we have the correct data...
            self.assertEqual(fields[0].field_name, b'foo')
            self.assertEqual(fields[0].value, b'bar')

            self.assertEqual(fields[1].field_name, b'test')
            self.assertEqual(fields[1].value, b'asdf')

            # ... and assert that we've finished.
            self.assertTrue(on_end.called)

        f = FormParser(b'application/x-www-form-urlencoded', on_field, on_file, on_end=on_end)
        self.assertTrue(isinstance(f.parser, QuerystringParser))
        simple_test(f)

        f = FormParser(b'application/x-url-encoded', on_field, on_file, on_end=on_end)
        self.assertTrue(isinstance(f.parser, QuerystringParser))
        simple_test(f)

    def test_close_methods(self):
        parser = Mock()
        f = FormParser(b'application/x-url-encoded', None, None)
        f.parser = parser

        f.finalize()
        parser.finalize.assert_called_once_with()

        f.close()
        parser.close.assert_called_once_with()

    def test_bad_content_type(self):
        # We should raise a ValueError for a bad Content-Type
        with self.assertRaises(ValueError):
            f = FormParser(b'application/bad', None, None)

    def test_no_boundary_given(self):
        # We should raise a FormParserError when parsing a multipart message
        # without a boundary.
        with self.assertRaises(FormParserError):
            f = FormParser(b'multipart/form-data', None, None)

    def test_bad_content_transfer_encoding(self):
        data = b'----boundary\r\nContent-Disposition: form-data; name="file"; filename="test.txt"\r\nContent-Type: text/plain\r\nContent-Transfer-Encoding: badstuff\r\n\r\nTest\r\n----boundary--\r\n'

        files = []
        def on_file(f):
            files.append(f)
        on_field = Mock()
        on_end = Mock()

        f = FormParser(b'multipart/form-data', on_field, on_file,
                       on_end=on_end, boundary=b'--boundary')

        with self.assertRaises(FormParserError):
            f.write(data)
            f.finalize()


class TestRequestBodyMixin(unittest.TestCase):
    def setUp(self):
        class TestClass(object):
            config = {}
            headers = {}

        class MixedIn(RequestBodyMixin, TestClass):
            pass

        self.m = MixedIn()

    def test_form_parser(self):
        self.m.headers[b'Content-Type'] = b'application/octet-stream'
        self.m.config['MAX_FIELD_SIZE'] = 1234

        f = self.m.form_parser(None, None)
        self.assertTrue(isinstance(f, FormParser))
        self.assertTrue(isinstance(f.parser, OctetStreamParser))
        self.assertEqual(f.config.get('MAX_FIELD_SIZE'), 1234)

    def test_form_parser_octet_stream(self):
        files = []
        def on_file(f):
            files.append(f)

        self.m.headers[b'Content-Type'] = b'application/octet-stream'
        self.m.headers[b'X-File-Name'] = b'foo.txt'

        f = self.m.form_parser(None, on_file)
        f.write(b'foobar')
        f.finalize()

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].file_name, b'foo.txt')

    def test_form_parser_multipart(self):
        # TODO: test more!
        pass

    def test_parse_body(self):
        # Load test data.
        test_file = 'single_field_single_file.http'
        with open(os.path.join(http_tests_dir, test_file), 'rb') as f:
            test_data = f.read()

        self.m.headers[b'Content-Type'] = b'multipart/form-data; boundary="boundary"'
        self.m.input_stream = BytesIO(test_data)
        self.m.parse_body()

        self.assertEqual(len(self.m.POST), 1)
        self.assertIn(b'field', self.m.POST)
        self.assertEqual(self.m.POST[b'field'].value, b'test1')

        self.assertEqual(len(self.m.files), 1)
        self.assertIn(b'file', self.m.files)
        file_class = self.m.files[b'file']
        self.assertEqual(file_class.file_name, b'file.txt')

        o = file_class.file_object
        o.seek(0)
        file_data = o.read()
        self.assertEqual(file_data, b'test2')

    def test_default_fields_files(self):
        self.assertEqual(self.m.GET, {})
        self.assertEqual(self.m.POST, {})
        self.assertEqual(self.m.fields, {})
        self.assertEqual(self.m.files, {})

    def test_errors_with_no_content_type(self):
        with self.assertRaises(ValueError):
            f = self.m.form_parser(None, None)

    # Helper for querystring assertions.
    def assert_fields(self, multidict, kvs):
        # Assert that we have all our data.
        _key = lambda f: (f[1].field_name, f[1].value)
        check = sorted(multidict.iteritems(multi=True), key=_key)

        # Make (name, Field) tuples from our given tuples.
        def _make(tup):
            return (tup[0], Field.from_value(tup[0], tup[1]))
        given = sorted(map(_make, kvs), key=_key)

        self.assertEqual(check, given)

    def test_parse_querystring(self):
        self.m.query_string = b'foo=bar&other=asdf&foo=other'
        self.m.parse_querystring()

        self.assert_fields(self.m.GET, [
            (b'foo', b'bar'),
            (b'foo', b'other'),
            (b'other', b'asdf'),
        ])

    def test_will_mix_querystring(self):
        # Load test data.
        test_file = 'single_field_single_file.http'
        with open(os.path.join(http_tests_dir, test_file), 'rb') as f:
            test_data = f.read()

        # Parse POST body.
        self.m.headers[b'Content-Type'] = b'multipart/form-data; boundary="boundary"'
        self.m.input_stream = BytesIO(test_data)
        self.m.parse_body()

        # Parse querystring.
        self.m.query_string = b'field=query&other=asdf'
        self.m.parse_querystring()

        self.assert_fields(self.m.fields, [
            (b'field', b'query'),
            (b'field', b'test1'),
            (b'other', b'asdf'),
        ])


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFile))
    suite.addTest(unittest.makeSuite(TestParseOptionsHeader))
    suite.addTest(unittest.makeSuite(TestBaseParser))
    suite.addTest(unittest.makeSuite(TestQuerystringParser))
    suite.addTest(unittest.makeSuite(TestOctetStreamParser))
    suite.addTest(unittest.makeSuite(TestBase64Decoder))
    suite.addTest(unittest.makeSuite(TestQuotedPrintableDecoder))
    suite.addTest(unittest.makeSuite(TestFormParser))
    suite.addTest(unittest.makeSuite(TestRequestBodyMixin))

    return suite

