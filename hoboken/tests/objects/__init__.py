from __future__ import with_statement, print_function


import os
import sys
import unittest

from .. import ensure_in_path
ensure_in_path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import hoboken


def suite():
    # Import test suites here.
    from .test_util import suite as suite_1
    from .test_request import suite as suite_2
    from .test_response import suite as suite_3
    from .test_headers import suite as suite_4
    from .test_mixins_accept import suite as suite_5
    from .test_mixins_authorization import suite as suite_6
    from .test_mixins_cache import suite as suite_7
    from .test_mixins_etag import suite as suite_8
    from .test_mixins_request_body import suite as suite_9
    from .test_mixins_request_building import suite as suite_10
    from .test_mixins_response_body import suite as suite_11
    from .test_mixins_user_agent import suite as suite_12

    suite = unittest.TestSuite()
    suite.addTest(suite_1())
    suite.addTest(suite_2())
    suite.addTest(suite_3())
    suite.addTest(suite_4())
    suite.addTest(suite_5())
    suite.addTest(suite_6())
    suite.addTest(suite_7())
    suite.addTest(suite_8())
    suite.addTest(suite_9())
    suite.addTest(suite_10())
    suite.addTest(suite_11())
    suite.addTest(suite_12())

    return suite


def main():
    """
    This runs the our tests, suitable for a command-line application
    """
    unittest.main(defaultTest='suite', exit=False)

if __name__ == "__main__":
    main()

