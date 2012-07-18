from .context import hoboken

import re

from nose.plugins.attrib import attr
from nose.tools import raises
from mock import patch


def test_RegexMatcher_compiles():
    with patch('re.compile') as mockobj:
        mockobj.return_value = 0

        test_re = "test_string"
        r = hoboken.matchers.RegexMatcher(test_re, [], [])

        assert isinstance(r, hoboken.matchers.RegexMatcher)
        mockobj.assert_called_with(test_re)


@raises(TypeError)
def test_RegexMatcher_invalid_regex():
    hoboken.matchers.RegexMatcher("asdf.(")


def test_RegexMatcher_fills_keys():
    test_re = "blah(.*?)middle(.*?)end"
    test_data = "blahFOOmiddleBARend"

    class TestWebRequest():
        path = test_data
        urlargs = ()
        urlvars = {}

    r = hoboken.matchers.RegexMatcher(test_re, [True, True], ['one', 'two'])
    webr = TestWebRequest()

    assert r.match(webr)
    assert webr.urlvars['_captures'] == ['FOO', 'BAR']
    assert webr.urlvars['one'] == 'FOO'
    assert webr.urlvars['two'] == 'BAR'

