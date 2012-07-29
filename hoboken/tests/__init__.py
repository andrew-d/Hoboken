from __future__ import with_statement, print_function

import os
import sys
import unittest
from webob import Request


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


ensure_in_path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import hoboken


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
            # raise exc_type, exc_value, tb  # This doesn't work on Python3
            raise exc_type
        return True


class BaseTestCase(unittest.TestCase):
    """
    This is the base class for all Hoboken base classes.  It adds some useful aliases for the
    camelCased names in the standard library (like nose).
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


class HobokenTestCase(BaseTestCase):
    """
    This is a testcase for Hoboken that contains helpful functions specifically for Hoboken
    """
    def setup(self):
        # We create an application for each test.
        self.app = hoboken.HobokenApplication(self.__class__.__name__)
        self.after_setup()

    def after_setup(self):
        """
        This is a hook for post-setup initialization.  Useful for e.g. creating routes
        """
        pass

    def body_func(self, req, resp):
        """
        This is a simple function that just returns some data, sufficient for testing a route
        """
        return 'request body'

    def call_app(self, path='/', method='GET', user_agent=None, host=None, accepts=None):
        """
        This function calls our application, and returns a tuple of (status, body)
        """
        req = Request.blank(path)
        req.method = method
        if user_agent is not None:
            req.headers['User-Agent'] = user_agent

        if host is not None:
            req.host = host

        if accepts is not None:
            req.accept = accepts

        resp = req.get_response(self.app)
        return resp.status_int, resp.text

    def assert_body_is(self, body, *args, **kwargs):
        """
        This is a helper function for the most common type of test: calling an application,
        and verifying that it succeeded and that the body matches a given set of data.
        """
        status, data = self.call_app(*args, **kwargs)
        self.assert_equal(status, 200)
        self.assert_equal(data, body)

    def assert_not_found(self, *args, **kwargs):
        """
        This is a helper function that simply asserts that a given request is not found
        """
        status, _ = self.call_app(*args, **kwargs)
        self.assert_equal(status, 404)


def suite():
    # Import test suites here.
    from .test_HobokenApplication import suite as suite_1
    from .test_RegexMatcher import suite as suite_2
    from .test_beforeafter import suite as suite_3
    from .test_conditions import suite as suite_4
    from .test_helpers import suite as suite_5
    from .test_routing import suite as suite_6

    suite = unittest.TestSuite()
    suite.addTest(suite_1())
    suite.addTest(suite_2())
    suite.addTest(suite_3())
    suite.addTest(suite_4())
    suite.addTest(suite_5())
    suite.addTest(suite_6())

    return suite


def main():
    """
    This runs the our tests, suitable for a command-line application
    """
    try:
        unittest.main(defaultTest='suite')
    except Exception as e:
        print("Exception: {0!s}".format(e))

if __name__ == "__main__":
    main()

