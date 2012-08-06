import re
import sys

__all__ = [
    "iscallable", "BaseStringType", "StringIO", "RegexType", "get_func_attr",
    "set_func_attr"
]

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

    def get_func_attr(func, attr, default=None, delete=False):
        if delete:
            return func.__dict__.pop(attr, default)
        else:
            return func.__dict__.get(attr, default)

    def set_func_attr(func, attr, value):
        func.__dict__[attr] = value

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

    def get_func_attr(func, attr, default=None, delete=False):
        if delete:
            return func.func_dict.pop(attr, default)
        else:
            return func.func_dict.get(attr, default)

    def set_func_attr(func, attr, value):
        func.func_dict[attr] = value


# Cross-Python stuff.
RegexType = type(re.compile(""))
RegexMatchType = type(re.compile(".*").match("asdf"))
