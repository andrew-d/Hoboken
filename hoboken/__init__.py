from __future__ import absolute_import
import sys

# This is the canonical package information.
__author__    = 'Andrew Dunham'
__license__   = 'Apache'
__copyright__ = "Copyright (c) 2012, Andrew Dunham"

# We get the version from a sub-file that can be automatically generated.
from ._version import __version__

# Set up logging here.
import logging
from .log import NullHandler
logging.getLogger(__name__).addHandler(NullHandler())

# Cleanup namespace
del NullHandler, logging

# Imports we import into the namespace.
from hoboken.application import HobokenBaseApplication, condition, halt, \
    pass_route

# Submodules we pull in here.
from . import matchers
from . import exceptions

# Grab mixins.
from hoboken.helpers import *


# Build our actual application.
class HobokenApplication(HobokenBaseApplication, HobokenCachingMixin,
                         HobokenRedirectMixin, HobokenRenderMixin):
    pass

# Create our extension module.
# This will first try and import a module from 'hoboken.builtin_ext.whatever',
# and, if that isn't found, from 'hoboken_whatever'.
from hoboken.exthook import ImportRedirector
ext = ImportRedirector('hoboken.ext', 'hoboken_%s',
                       builtins='hoboken.builtin_ext').module
