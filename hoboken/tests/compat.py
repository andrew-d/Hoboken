try:
    import unittest2 as unittest
except ImportError:
    import unittest

import os
import sys

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

