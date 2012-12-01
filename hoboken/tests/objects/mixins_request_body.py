# -*- coding: utf-8 -*-

from . import BaseTestCase, skip
import unittest
from io import BytesIO
from mock import MagicMock, Mock, patch

from hoboken.objects.mixins.request_body import *


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
        self.p.write(b'')

        self.assert_fields((b'foo', b'bar'))

    def test_querystring_blank_beginning(self):
        self.p.write(b'&foo=bar')
        self.p.write(b'')

        self.assert_fields((b'foo', b'bar'))

    def test_querystring_blank_end(self):
        self.p.write(b'foo=bar&')
        self.p.write(b'')

        self.assert_fields((b'foo', b'bar'))

    def test_multiple_querystring(self):
        self.p.write(b'foo=bar&asdf=baz')
        self.p.write(b'')

        self.assert_fields(
            (b'foo', b'bar'),
            (b'asdf', b'baz')
        )

    def test_streaming_simple(self):
        self.p.write(b'foo=bar&')
        self.assert_fields(
            (b'foo', b'bar'),
        )

        self.p.write(b'asdf=baz')
        self.p.write(b'')
        self.assert_fields(
            (b'asdf', b'baz')
        )

    def test_streaming_break(self):
        self.p.write(b'foo=one')
        self.assert_fields()

        self.p.write(b'two')
        self.assert_fields()

        self.p.write(b'three')
        self.assert_fields()

        self.p.write(b'&asd')
        self.assert_fields(
            (b'foo', b'onetwothree')
        )

        self.p.write(b'f=baz')
        self.p.write(b'')
        self.assert_fields(
            (b'asdf', b'baz')
        )

    def test_semicolon_seperator(self):
        self.p.write(b'foo=bar;asdf=baz')
        self.p.write(b'')

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

    def assert_data(self, data):
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
        self.p.write(b'')
        self.assert_finished()

    def test_multiple_chunks(self):
        self.p.write(b'foo')
        self.p.write(b'bar')
        self.p.write(b'baz')
        self.p.write(b'')

        self.assert_data(b'foobarbaz')
        self.assert_finished()


class TestBase64Decoder(BaseTestCase):
    # Note: base64('foobar') == 'Zm9vYmFy'
    def setup(self):
        self.f = BytesIO()
        self.d = Base64Decoder(self.f)

    def assert_data(self, data):
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

            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foo')

    def test_long_bad_split(self):
        buff = b'Zm9vYmFy'
        for i in range(5, 8):
            first, second = buff[:i], buff[i:]

            self.d.write(first)
            self.d.write(second)
            self.assert_data(b'foobar')


class TestQuotedPrintableDecoder(BaseTestCase):
    def setup(self):
        self.f = BytesIO()
        self.d = QuotedPrintableDecoder(self.f)

    def assert_data(self, data):
        self.f.seek(0)
        self.assert_equal(self.f.read(), data)
        self.f.seek(0)
        self.f.truncate()

    def test_simple(self):
        self.d.write(b'foobar')
        self.d.write(b'')

        self.assert_data(b'foobar')

    def test_with_escape(self):
        self.d.write(b'foo=3Dbar')
        self.d.write(b'')

        self.assert_data(b'foo=bar')

    def test_with_newline_escape(self):
        self.d.write(b'foo=\r\nbar')
        self.d.write(b'')

        self.assert_data(b'foobar')

        self.d.write(b'foo=\nbar')
        self.d.write(b'')

        self.assert_data(b'foobar')

    def test_with_split_escape(self):
        self.d.write(b'foo=3')
        self.d.write(b'Dbar')
        self.d.write(b'')

        self.assert_data(b'foo=bar')

    def test_with_split_newline_escape(self):
        self.d.write(b'foo=\r')
        self.d.write(b'\nbar')
        self.d.write(b'')

        self.assert_data(b'foobar')


class TestRequestBodyMixin(BaseTestCase):
    def setup(self):
        pass


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestParseOptionsHeader))
    suite.addTest(unittest.makeSuite(TestQuerystringParser))
    suite.addTest(unittest.makeSuite(TestOctetStreamParser))
    suite.addTest(unittest.makeSuite(TestBase64Decoder))
    suite.addTest(unittest.makeSuite(TestQuotedPrintableDecoder))
    suite.addTest(unittest.makeSuite(TestRequestBodyMixin))

    return suite

