# -*- coding: utf-8 -*-

from . import HobokenTestCase, BaseTestCase, is_python3
from ..matchers import BasicMatcher, RegexMatcher, HobokenRouteMatcher
from .helpers import parametrize, parameters

import re
import os
import sys
import yaml
import unittest
from mock import patch, MagicMock

class TestBasicMatcher(BaseTestCase):
    def test_basic_matcher(self):
        m = BasicMatcher('/foobar')
        req = MagicMock(path_info="/foobar")

        matches, _, _ = m.match(req)
        self.assert_true(matches)

    def test_basic_matcher_case_insensitive(self):
        m = BasicMatcher('/foobar', case_sensitive=False)
        req = MagicMock(path_info="/FOOBAR")

        matches, _, _ = m.match(req)
        self.assert_true(matches)

    def test_will_reverse(self):
        m = BasicMatcher('/foobar')
        self.assert_equal(m.reverse(None, None), '/foobar')


class TestRegexMatcher(BaseTestCase):
    def test_compiles(self):
        with patch('re.compile') as mock_obj:
            mock_obj.return_value = 0

            test_re = "test_string"
            r = RegexMatcher(test_re, [], [])

            self.assert_is_instance(r, RegexMatcher)
            mock_obj.assert_called_with(test_re)

    def test_raises_on_invalid(self):
        with self.assert_raises(TypeError):
            _ = RegexMatcher("asdf.(")

        with self.assert_raises(TypeError):
            _ = RegexMatcher(123)

    def test_fills_keys(self):
        test_re = "blah(.*?)middle(.*?)end"
        test_data = "blahFOOmiddleBARend"

        m = RegexMatcher(test_re, [True, True], ['one', 'two'])
        req = MagicMock(path_info=test_data)

        matches, args, kwargs = m.match(req)
        self.assert_true(matches)
        self.assert_in('one', kwargs)
        self.assert_in('two', kwargs)

        self.assert_equal(kwargs['one'], 'FOO')
        self.assert_equal(kwargs['two'], 'BAR')

        self.assert_in('_captures', kwargs)
        self.assert_equal(kwargs['_captures'], ['FOO', 'BAR'])

    def test_with_existing_regex(self):
        r = re.compile("/foob(.*?)ar")
        m = RegexMatcher(r, [False], [None])

        req = MagicMock(path_info='/foobAAAAAAAAAAAAAar')

        matches, args, _  = m.match(req)
        self.assert_true(matches)
        self.assert_equal(args, ['AAAAAAAAAAAAA'])

    def test_reverse(self):
        m = RegexMatcher("/asdf", [], [])
        self.assert_false(m.reverse(None, None))

# Load our list of test cases from our yaml file.
curr_dir = os.path.abspath(os.path.dirname(__file__))
test_file = os.path.join(curr_dir, 'reversing_tests.yaml')
with open(test_file, 'rb') as f:
    file_data = f.read()
test_cases = list(yaml.load_all(file_data))

def make_name(idx, param):
    return "test_" + param['name']

@parametrize
class TestHobokenRouteMatcher(BaseTestCase):
    @parameters(test_cases, name_func=make_name)
    def test_handles_unicode(self, param):
        path = param['path']
        args = param.get('args', [])
        kwargs = param.get('kwargs', {})

        m = HobokenRouteMatcher(path)
        out = m.reverse(args, kwargs)

        self.assert_equal(out, param['reverse'])

    def test_reversing(self):
        if is_python3():
            return

        unicode_str = b'/f\xc3\xb8\xc3\xb8'.decode('utf-8')

        m = HobokenRouteMatcher(unicode_str)
        request = MagicMock(path_info="/f%C3%B8%C3%B8")
        matches, _, _ = m.match(request)
        self.assert_true(matches)


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(TestBasicMatcher))
    suite.addTest(unittest.makeSuite(TestRegexMatcher))
    suite.addTest(unittest.makeSuite(TestHobokenRouteMatcher))

    return suite

