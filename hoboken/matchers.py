# Future-proofing
from __future__ import with_statement, absolute_import

# Stdlib dependencies
import re

# In-package dependencies
from .exceptions import *
from .compat import *


class BasicMatcher(object):
    """
    Basic matcher - just checks if the path matches exactly.
    """
    def __init__(self, path, case_sensitive=True):
        self.path = path
        self.case_sensitive = case_sensitive

    def match(self, webr):
        if self.case_sensitive:
            return self.path == webr.path
        else:
            return self.path.lower() == webr.path.lower()


class RegexMatcher(object):
    """
    This class matches a URL using a provided regex.
    """

    def __init__(self, regex, keys):
        # We handle regexes and string patterns for regexes here.
        if isinstance(regex, RegexType):
            self.re = regex
        elif isinstance(regex, BaseStringType):
            try:
                self.re = re.compile(regex)
            except re.error:
                raise TypeError("Parameter 'regex' is not a valid regex")
        else:
            raise TypeError("Parameter 'regex' is not a valid regex")

        # Save keys.
        self.keys = keys

    def match(self, webr):
        match = self.re.match(webr.path)
        if match:
            matches = match.groups()

            # Create lists for our splat parameter.
            webr.route_params["splat"] = []

            # Merge in the captures.
            for k, v in zip(self.keys, matches):
                # If we have no key, then we do nothing.  This occurs, for example,
                # when we are passed a regex with an unnamed group.
                if k is None:
                    continue

                # If the key already exists and is a list, we append.  Otherwise,
                # we simply overwrite the parameter if the value is non-None.
                if k in webr.route_params and isinstance(webr.route_params[k], list):
                    webr.route_params[k].append(v)
                elif v:
                    webr.route_params[k] = v

            # We save all captures in the special parameter "_captures".
            webr.route_params["_captures"] = list(matches)

            # Success!
            return True
        else:
            return False
