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
    from .util import suite as suite_1
    from .request import suite as suite_2
    from .response import suite as suite_3
    from .headers import suite as suite_4
    from .mixins_accept import suite as suite_5
    from .mixins_cache import suite as suite_6
    from .mixins_response_body import suite as suite_7

    suite = unittest.TestSuite()
    suite.addTest(suite_1())
    suite.addTest(suite_2())
    suite.addTest(suite_3())
    suite.addTest(suite_4())
    suite.addTest(suite_5())
    suite.addTest(suite_6())
    suite.addTest(suite_7())

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

