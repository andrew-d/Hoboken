from __future__ import absolute_import
import sys

# This is the canonical package information.
__author__  = 'Andrew Dunham'
__license__ = 'Apache'
__copyright__ = "Copyright (c) 2012, Andrew Dunham"

# We get the version from a sub-file that can be automatically generated,
from ._version import __version__

# Imports we import into the namespace.
from .application import HobokenBaseApplication, condition, halt, \
        pass_route

# Submodules we pull in here.
from . import matchers
from . import exceptions

# Grab mixins.
from .helpers import *

# Build our actual application.
class HobokenApplication(HobokenBaseApplication, HobokenCachingMixin, HobokenRedirectMixin, HobokenRenderMixin):
    pass
