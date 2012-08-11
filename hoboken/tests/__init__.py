from __future__ import with_statement, print_function

from .helpers import *

import os
import unittest
from webob import Request

ensure_in_path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import hoboken


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

    def body_func(self):
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
    from .test_matchers import suite as suite_2
    from .test_beforeafter import suite as suite_3
    from .test_conditions import suite as suite_4
    from .test_helpers import suite as suite_5
    from .test_routing import suite as suite_6
    from .test_request_response import suite as suite_7
    from .test_ext import suite as suite_8

    suite = unittest.TestSuite()
    suite.addTest(suite_1())
    suite.addTest(suite_2())
    suite.addTest(suite_3())
    suite.addTest(suite_4())
    suite.addTest(suite_5())
    suite.addTest(suite_6())
    suite.addTest(suite_7())
    suite.addTest(suite_8())

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

