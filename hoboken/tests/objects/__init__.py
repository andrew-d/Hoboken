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

    suite = unittest.TestSuite()
    suite.addTest(suite_1())
    suite.addTest(suite_2())

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

