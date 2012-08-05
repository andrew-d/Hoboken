from . import HobokenTestCase, BaseTestCase
from ..matchers import BasicMatcher, RegexMatcher
import unittest

from mock import patch, MagicMock
import re

class TestBasicMatcher(BaseTestCase):
    def test_basic_matcher(self):
        m = BasicMatcher('/foobar')
        req = MagicMock(path="/foobar")

        matches, _, _ = m.match(req)
        self.assert_true(matches)

    def test_basic_matcher_case_insensitive(self):
        m = BasicMatcher('/foobar', case_sensitive=False)
        req = MagicMock(path="/FOOBAR")

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
            RegexMatcher("asdf.(")

    def test_fills_keys(self):
        test_re = "blah(.*?)middle(.*?)end"
        test_data = "blahFOOmiddleBARend"

        m = RegexMatcher(test_re, [True, True], ['one', 'two'])
        req = MagicMock(path=test_data)

        matches, args, kwargs = m.match(req)
        self.assert_true(matches)
        self.assert_in('one', kwargs)
        self.assert_in('two', kwargs)

        self.assert_equal(kwargs['one'], 'FOO')
        self.assert_equal(kwargs['two'], 'BAR')

        self.assert_in('_captures', kwargs)
        self.assert_equal(kwargs['_captures'], ['FOO', 'BAR'])

        # TODO: test urlargs too

    def test_with_existing_regex(self):
        r = re.compile("/foob(.*?)ar")
        m = RegexMatcher(r, [False], [None])

        req = MagicMock(path='/foobAAAAAAAAAAAAAar')

        matches, args, _  = m.match(req)
        self.assert_true(matches)
        self.assert_equal(args, ['AAAAAAAAAAAAA'])

    def test_reverse(self):
        m = RegexMatcher("/asdf", [], [])
        self.assert_false(m.reverse(None, None))


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(TestRegexMatcher))

    return suite

