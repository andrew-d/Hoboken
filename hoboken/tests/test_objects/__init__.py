from __future__ import with_statement, print_function

# Import helpers for our submodules to pull in, and also import everything
# from it for our own use.
from .. import helpers
from ..helpers import *

import os
import unittest

ensure_in_path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
import hoboken


def suite():
    # Import test suites here.
    from .test_util import suite as suite_1
    from .test_request import suite as suite_2
    from .test_response import suite as suite_3
    from .test_headers import suite as suite_4
    from .test_mixins_accept import suite as suite_5
    from .test_mixins_cache import suite as suite_6
    from .test_mixins_request_body import suite as suite_7
    from .test_mixins_request_building import suite as suite_8
    from .test_mixins_response_body import suite as suite_9
    from .test_mixins_etag import suite as suite_10

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

    return suite


def main():
    """
    This runs the our tests, suitable for a command-line application
    """
    unittest.main(defaultTest='suite', exit=False)
    print("Number of assertions: {0}".format(BaseTestCase.number_of_assertions))
    print("")

if __name__ == "__main__":
    main()

