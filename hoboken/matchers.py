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

    def __init__(self, regex, key_types, key_names):
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
        self.key_types = key_types
        self.key_names = key_names

    def match(self, webr):
        match = self.re.match(webr.path)
        if match:
            matches = match.groups()

            # Merge in the captures.
            for t, k, v in zip(self.key_types, self.key_names, matches):
                # Depending on the type, either add to urlargs or urlparams.
                if t == True:
                    if k is not None:
                        webr.urlvars[k] = v
                else:
                    webr.urlargs = webr.urlargs + (v,)

            # We save all captures in the special parameter "_captures".
            webr.urlvars["_captures"] = list(matches)

            # Success!
            return True
        else:
            return False

    def __str__(self):
        return self.re.pattern

    def __repr__(self):
        return "RegexMatcher(regex={0!r}, key_types={1!r}, key_names={2!r})".format(self.re.pattern, self.key_types, self.key_names)

