from __future__ import with_statement

import os
import sys
import types
import unittest
import functools

from ..six import iteritems, PY3


def ensure_in_path(path):
    """
    Ensure that a given path is in the sys.path array
    """
    if not os.path.isdir(path):
        raise RuntimeError('Tried to add nonexisting path')

    def _samefile(x, y):
        try:
            return os.path.samefile(x, y)
        except (IOError, OSError):
            return False
        except AttributeError:
            # Probably on Windows.
            path1 = os.path.abspath(x).lower()
            path2 = os.path.abspath(y).lower()
            return path1 == path2

    # Remove existing copies of it.
    for pth in sys.path:
        if _samefile(pth, path):
            sys.path.remove(pth)

    # Add it at the beginning.
    sys.path.insert(0, path)


# This will pull in the skip() function from the unittest module, or, if it
# doesn't exist, will make a decorator that simply returns a dummy class or
# function, as appropriate.
if hasattr(unittest, 'skip'):
    skip = unittest.skip
else:
    def skip(reason):
        def decorator(obj):
            if isinstance(obj, object):
                class Nothing(object):
                    pass

                return Nothing
            else:
                def internal_function(*args, **kwargs):
                    return None
                return internal_function

        return decorator

if hasattr(unittest, 'skipIf'):
    skip_if = unittest.skipIf
else:
    def skip_if(condition, reason):
        if condition:
            return skip(reason)
        else:
            def nop(obj):
                return obj
            return nop


def is_pypy():
    return hasattr(sys, 'pypy_version_info')

def is_python3():
    return PY3


class _ExceptionCatcher(object):
    """
    This is a context manager that asserts that a particular exception was raised
    during it.  This was borrowed from Mitsuhiko's flask testing code.
    """
    def __init__(self, test_case, exc_type):
        self.test_case = test_case
        self.exc_type = exc_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        exception_name = self.exc_type.__name__
        if exc_type is None:
            self.test_case.fail('Expected exception of type %r' % exception_name)
        elif not issubclass(exc_type, self.exc_type):
            raise exc_type(exc_value)
        return True


class BaseTestCase(unittest.TestCase):
    """
    This TestCase subclass adds some useful aliases for the camelCased names
    in the standard library (like nose).
    """

    def assert_equal(self, x, y):
        return self.assertEqual(x, y)

    def assert_not_equal(self, x, y):
        return self.assertNotEqual(x, y)

    def assert_true(self, x):
        return self.assertTrue(x)

    def assert_false(self, x):
        return self.assertFalse(x)

    def assert_in(self, x, y):
        assert x in y, "{0!r} is not in {1!r}".format(x, y)

    def assert_raises(self, exception, callable=None, *args, **kwargs):
        catcher = _ExceptionCatcher(self, exception)
        if callable is None:
            return catcher
        with catcher:
            callable(*args, **kwargs)

    def assert_is_instance(self, obj, type):
        assert isinstance(obj, type), "{0!r} is not an instance of type {1!r}".format(obj, type)

    def setup(self):
        """This is a non-camelCase hook that is identical to setUp"""
        pass

    def teardown(self):
        """This is a non-camelCase hook that is identical to tearDown"""
        pass

    def setUp(self):
        self.setup()

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        self.teardown()


def parameters(params_list, name_func=None):
    """
    This function decorates a function, marking it as a function in a class
    to be parametrized.  This is then used by the parametrize() class decorator
    and associated metaclass, below, to dynamically replace copies of the
    associated methods with parametrized versions.
    """
    def internal_decorator(func):
        if is_python3():
            func.__dict__['params'] = params_list
            func.__dict__['name_func'] = name_func
        else:
            func.func_dict['params'] = params_list
            func.func_dict['name_func'] = name_func
        return func

    return internal_decorator


class ParametrizingMetaclass(type):
    def __new__(klass, name, bases, attrs):
        new_attrs = attrs.copy()
        for attr_name, attr in iteritems(attrs):
            # We only care about functions
            if not isinstance(attr, types.FunctionType):
                continue

            if is_python3():
                func_dict = attr.__dict__
            else:
                func_dict = attr.func_dict

            # If the function doesn't have a 'params' attribute,
            # we ignore it.
            if 'params' not in func_dict:
                continue
            else:
                params = func_dict['params']

            # Either use the name function...
            name_func = func_dict['name_func']

            # ... or default to one that just returns the function name plus
            # the number of the parameter.
            if name_func is None:
                name_func = lambda i, p: attr_name + str(i)

            for i, param in enumerate(params):
                # Get the name for this parameter.
                new_name = name_func(i, param)

                # This is a pseudo-decorator that, given a function and a
                # parameter, will return a function that will call the
                # function with the given parameter.  The only difference is
                # that it will set the __name__ parameter of the function to
                # the new_name value from the scope, above.
                def create_method(func, call_param):
                    old_method = func

                    # functools.wraps() here ensures we copy the various
                    # special attributes like __doc__, and the function
                    # dict, over.
                    @functools.wraps(func)
                    def new_method(self):
                        return old_method(self, call_param)

                    # We manually override the name, since the wraps() method
                    # might clobber that.
                    new_method.__name__ = new_name

                    if is_python3():
                        new_dict = new_method.__dict__
                    else:
                        new_dict = new_method.func_dict

                    # Also, we remove the two attributes we've added from the
                    # function's dict (but don't error if they're not there).
                    new_dict.pop("params", None)
                    new_dict.pop("name_func", None)
                    return new_method

                # We create our parametrized method, and then assign it to our
                # new arguments dict.
                parametrized_method = create_method(attr, param)
                new_attrs[new_name] = parametrized_method

            # Remove the old attribute from the new dict.
            del new_attrs[attr_name]

        # We create the class as normal, except we use our new attributes.
        return type.__new__(klass, name, bases, new_attrs)


def parametrize(klass):
    """
    This is a class decorator that simply creates the class as normal, except
    that it uses the ParametrizingMetaclass in a Python 2/3 agnostic manner.
    """
    return ParametrizingMetaclass(klass.__name__, klass.__bases__, klass.__dict__)


