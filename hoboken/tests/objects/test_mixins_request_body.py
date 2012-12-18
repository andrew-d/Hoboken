# -*- coding: utf-8 -*-

import os
import sys
import glob
import yaml
import tempfile
import unittest
from io import BytesIO

import pytest
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

    def test_file_fallback(self):
        self.c['MAX_MEMORY_FILE_SIZE'] = 1

        self.f.write(b'1')
        self.assertTrue(self.f.in_memory)
        self.assert_data(b'1')

        self.f.write(b'123')
        self.assertFalse(self.f.in_memory)
        self.assert_data(b'123')

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
        self.assertTrue(self.f.actual_file_name is not None)
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


class TestQuerystringParser(unittest.TestCase):
    def on_field(self, val):
        self.f.append(val)

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


class TestFormParser(object):
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
        assert file_data == data

    def assert_file(self, field_name, file_name, data):
        # Find this file.
        found = None
        for f in self.files:
            if f.field_name == field_name:
                found = f
                break

        # Assert that we found it.
        assert found is not None

        try:
            # Assert about this file.
            self.assert_file_data(found, data)
            assert found.file_name == file_name

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
        assert found is not None
        assert value == found.value

        # Remove it for future iterations.
        self.fields.remove(found)

    @pytest.mark.parametrize('param', http_tests)
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
        print("")
        print(repr(self.fields))
        print(repr(self.files))

        assert processed == len(param['test'])

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
            assert i == len(test_data)

            # Assert that our file and field are here.
            self.assert_field(b'field', b'test1')
            self.assert_file(b'file', b'file.txt', b'test2')

    def test_bad_start_boundary(self):
        self.make(b'boundary')
        data = b'--boundary\rfoobar'
        i = self.f.write(data)
        assert i != len(data)

        self.make(b'boundary')
        data = b'--boundaryfoobar'
        i = self.f.write(data)
        assert i != len(data)

    def test_octet_stream(self):
        files = []
        def on_file(f):
            files.append(f)
        on_field = Mock()
        on_end = Mock()

        f = FormParser(b'application/octet-stream', on_field, on_file, on_end=on_end, file_name=b'foo.txt')
        assert isinstance(f.parser, OctetStreamParser)

        f.write(b'test')
        f.write(b'1234')
        f.finalize()

        assert not on_field.called
        assert len(files) == 1
        self.assert_file_data(files[0], b'test1234')
        assert on_end.called

    def test_querystring(self):
        fields = []
        def on_field(f):
            fields.append(f)
        on_file = Mock()
        on_end = Mock()

        def simple_test(f):
            del fields[:]
            on_end.reset_mock()

            f.write(b'foo=bar')
            f.write(b'&test=asdf')
            f.finalize()

            assert not on_file.called
            assert len(fields) == 2

            assert fields[0].field_name == b'foo'
            assert fields[0].value == b'bar'

            assert fields[1].field_name == b'test'
            assert fields[1].value == b'asdf'

            assert on_end.called

        f = FormParser(b'application/x-www-form-urlencoded', on_field, on_file, on_end=on_end)
        assert isinstance(f.parser, QuerystringParser)
        simple_test(f)

        f = FormParser(b'application/x-url-encoded', on_field, on_file, on_end=on_end)
        assert isinstance(f.parser, QuerystringParser)
        simple_test(f)

    def test_close_methods(self):
        parser = Mock()
        f = FormParser(b'application/x-url-encoded', None, None)
        f.parser = parser

        f.finalize()
        parser.finalize.assert_called_once_with()

        f.close()
        parser.close.assert_called_once_with()


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

        self.assertEqual(len(self.m.fields), 1)
        self.assertTrue(b'field' in self.m.fields)
        self.assertEqual(self.m.fields[b'field'].value, b'test1')

        self.assertEqual(len(self.m.files), 1)
        self.assertTrue(b'file' in self.m.files)
        file_class = self.m.files[b'file']
        self.assertEqual(file_class.file_name, b'file.txt')

        o = file_class.file_object
        o.seek(0)
        file_data = o.read()
        self.assertEqual(file_data, b'test2')

    def test_default_fields_files(self):
        self.assertEqual(self.m.fields, [])
        self.assertEqual(self.m.files, [])

    def test_errors_with_no_content_type(self):
        with self.assertRaises(ValueError):
            f = self.m.form_parser(None, None)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFile))
    suite.addTest(unittest.makeSuite(TestParseOptionsHeader))
    suite.addTest(unittest.makeSuite(TestQuerystringParser))
    suite.addTest(unittest.makeSuite(TestOctetStreamParser))
    suite.addTest(unittest.makeSuite(TestBase64Decoder))
    suite.addTest(unittest.makeSuite(TestQuotedPrintableDecoder))
    # suite.addTest(unittest.makeSuite(TestFormParser))
    suite.addTest(unittest.makeSuite(TestRequestBodyMixin))

    return suite

