import re
import sys

__all__ = ["iscallable", "BaseStringType", "StringIO", "RegexType"]

# Determine Python version.
python_version = sys.version_info[:3]
is_python3 = python_version >= (3, 0, 0)

if is_python3:
    import collections

    # callable() replacement
    def iscallable(f):
        return isinstance(f, collections.Callable)

    # basestring
    BaseStringType = str

    # StringIO
    from io import StringIO
else:
    def iscallable(f):
        return callable(f)

    # basestring
    BaseStringType = basestring

    # StringIO
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


# Cross-Python stuff.
RegexType = type(re.compile(""))
RegexMatchType = type(re.compile(".*").match("asdf"))
