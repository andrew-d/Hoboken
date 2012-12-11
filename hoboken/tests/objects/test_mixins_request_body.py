# -*- coding: utf-8 -*-

from . import BaseTestCase, skip, parametrize, parameters
import os
import glob
import yaml
import tempfile
import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.request_body import *


# Get the current directory for our later test cases.
curr_dir = os.path.abspath(os.path.dirname(__file__))


class TestFile(BaseTestCase):
    def setup(self):
        self.c = {}
        self.d = tempfile.mkdtemp()
        self.f = File('foo.txt', config=self.c)

    def assert_data(self, data):
        f = self.f.file_object
        f.seek(0)
        self.assert_equal(f.read(), data)
        f.seek(0)
        f.truncate()

    def assert_exists(self):
        full_path = os.path.join(self.d, self.f.file_name)
        self.assert_true(os.path.exists(full_path))

    def test_simple(self):
        self.f.write(b'foobar')
        self.assert_data(b'foobar')

    def test_file_fallback(self):
        self.c['MAX_MEMORY_FILE_SIZE'] = 1

        self.f.write(b'1')
        self.assert_true(self.f.in_memory)
        self.assert_data(b'1')

        self.f.write(b'123')
        self.assert_false(self.f.in_memory)
        self.assert_data(b'123')

    def test_file_fallback_with_data(self):
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        self.f.write(b'1' * 10)
        self.assert_true(self.f.in_memory)

        self.f.write(b'2' * 10)
        self.assert_false(self.f.in_memory)

        self.assert_data(b'11111111112222222222')

    def test_file_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = self.d
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assert_false(self.f.in_memory)

        # Assert that the file exists
        self.assert_true(self.f.file_name is not None)
        self.assert_exists()

    def test_file_full_name(self):
        # Write to this dir.
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assert_false(self.f.in_memory)

        # Assert that the file exists
        self.assert_equal(self.f.file_name, 'foo')
        self.assert_exists()

    def test_file_full_name_with_ext(self):
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assert_false(self.f.in_memory)

        # Assert that the file exists
        self.assert_equal(self.f.file_name, 'foo.txt')
        self.assert_exists()

    def test_file_full_name_with_ext(self):
        self.c['UPLOAD_DIR'] = self.d
        self.c['UPLOAD_KEEP_FILENAME'] = True
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assert_false(self.f.in_memory)

        # Assert that the file exists
        self.assert_equal(self.f.file_name, 'foo.txt')
        self.assert_exists()

    def test_no_dir_with_extension(self):
        self.c['UPLOAD_KEEP_EXTENSIONS'] = True
        self.c['MAX_MEMORY_FILE_SIZE'] = 10

        # Write.
        self.f.write(b'12345678901')
        self.assert_false(self.f.in_memory)

        # Assert that the file exists
        ext = os.path.splitext(self.f.file_name)[1]
        self.assert_equal(ext, '.txt')
        self.assert_exists()

    # TODO: test uploading two files with the same name.


class TestParseOptionsHeader(BaseTestCase):
    def test_simple(self):
        t, p = parse_options_header(b'application/json')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {})

    def test_blank(self):
        t, p = parse_options_header(b'')
        self.assert_equal(t, b'')
        self.assert_equal(p, {})

    def test_single_param(self):
        t, p = parse_options_header(b'application/json;par=val')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'par': b'val'})

    def test_single_param_with_spaces(self):
        t, p = parse_options_header(b'application/json;     par=val')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'par': b'val'})

    def test_multiple_params(self):
        t, p = parse_options_header(b'application/json;par=val;asdf=foo')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'par': b'val', b'asdf': b'foo'})

    def test_quoted_param(self):
        t, p = parse_options_header(b'application/json;param="quoted"')
        self.assert_equal(t, b'application/json')
        self.assert_equal(p, {b'param': b'quoted'})

    def test_quoted_param_with_semicolon(self):
        t, p = parse_options_header(b'application/json;param="quoted;with;semicolons"')
        self.assert_equal(p[b'param'], b'quoted;with;semicolons')

    def test_quoted_param_with_escapes(self):
        t, p = parse_options_header(b'application/json;param="This \\" is \\" a \\" quote"')
        self.assert_equal(p[b'param'], b'This " is " a " quote')

    def test_handles_ie6_bug(self):
        t, p = parse_options_header(b'text/plain; filename="C:\\this\\is\\a\\path\\file.txt"')

        self.assert_equal(p[b'filename'], b'file.txt')


class TestQuerystringParser(BaseTestCase):
    def on_field(self, val):
        self.f.append(val)

    def assert_fields(self, *args, **kwargs):
        if kwargs.pop('finalize', True):
            self.p.finalize()

        self.assert_equal(self.f, list(args))
        if kwargs.get('reset', True):
            self.f = []

    def setup(self):
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


class TestOctetStreamParser(BaseTestCase):
    def setup(self):
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
        self.assert_equal(b''.join(self.d), data)
        self.d = []

    def assert_started(self, val=True):
        if val:
            self.assert_equal(self.started, 1)
        else:
            self.assert_equal(self.started, 0)

    def assert_finished(self, val=True):
        if val:
            self.assert_equal(self.finished, 1)
        else:
            self.assert_equal(self.finished, 0)

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


class TestBase64Decoder(BaseTestCase):
    # Note: base64('foobar') == 'Zm9vYmFy'
    def setup(self):
        self.f = BytesIO()
        self.d = Base64Decoder(self.f)

    def assert_data(self, data, finalize=True):
        if finalize:
            self.d.finalize()

        self.f.seek(0)
        self.assert_equal(self.f.read(), data)
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

            self.setup()
            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foo')

    def test_long_bad_split(self):
        buff = b'Zm9vYmFy'
        for i in range(5, 8):
            first, second = buff[:i], buff[i:]

            self.setup()
            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foobar')


class TestQuotedPrintableDecoder(BaseTestCase):
    def setup(self):
        self.f = BytesIO()
        self.d = QuotedPrintableDecoder(self.f)

    def assert_data(self, data, finalize=True):
        if finalize:
            self.d.finalize()

        self.f.seek(0)
        self.assert_equal(self.f.read(), data)
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


@parametrize
class TestFormParser(BaseTestCase):
    def make(self, param):
        boundary = param['result']['boundary']

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
        self.f = FormParser('multipart/form-data', on_field, on_file, on_end, boundary=boundary)

    @parameters(http_tests,
                name_func=lambda idx, param: 'test_' + param['name'])
    def test_http(self, param):
        # Firstly, create our parser with the given boundary.
        self.make(param)

        # Now, we feed the parser with data.
        processed = self.f.write(param['test'])
        self.assert_equal(processed, len(param['test']))
        self.f.finalize()

        # print(repr(param))
        print("")
        print(repr(self.fields))
        print(repr(self.files))

        # Assert that the parser gave us the appropriate fields/files.
        for e in param['result']['expected']:
            # something with e['type'], e['data'], and e['name']
            if e['type'] == 'field':
                # Find this field in our fields list.
                found = None
                for f in self.fields:
                    if f.field_name == e['name']:
                        found = f
                        break

                # Assert that it exists and matches.
                self.assert_true(found is not None)
                self.assert_equal(e['data'], found.value)

                # Remove it for future iterations.
                self.fields.remove(found)
            elif e['type'] == 'file':
                pass
            else:
                assert False


class TestRequestBodyMixin(BaseTestCase):
    def setup(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestFile))
    suite.addTest(unittest.makeSuite(TestParseOptionsHeader))
    suite.addTest(unittest.makeSuite(TestQuerystringParser))
    suite.addTest(unittest.makeSuite(TestOctetStreamParser))
    suite.addTest(unittest.makeSuite(TestBase64Decoder))
    suite.addTest(unittest.makeSuite(TestQuotedPrintableDecoder))
    suite.addTest(unittest.makeSuite(TestFormParser))
    suite.addTest(unittest.makeSuite(TestRequestBodyMixin))

    return suite

