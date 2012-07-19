from . import HobokenTestCase, BaseTestCase
from ..matchers import RegexMatcher
import unittest

from mock import patch, MagicMock
import re

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

        self.assert_true(m.match(req))
        req.urlvars.__setitem__.assert_any_call('one', 'FOO')
        req.urlvars.__setitem__.assert_any_call('two', 'BAR')
        req.urlvars.__setitem__.assert_any_call('_captures', ['FOO', 'BAR'])

        # TODO: test urlargs too


def suite():
    suite = unittest.TestSuite()

    suite.addTest(unittest.makeSuite(TestRegexMatcher))

    return suite

