# Future-proofing
from __future__ import with_statement, absolute_import

# Stdlib dependencies
import re
import urllib
#from functools import wraps

# External dependencies
from webob import Request, Response
from webob.exc import HTTPMethodNotAllowed, HTTPNotFound

# In-package dependencies
from .exceptions import *
from .compat import *


class WebRequest(Request):
    """
    This class represents a request.  It is comprised of:
     - The underlying WebOb Request object
     - Parameters from the route matcher
     - Instance variables, set by any before/after filters
    """
    def __init__(self, *args, **kwargs):
        super(WebRequest, self).__init__(*args, **kwargs)
        self.route_params = {}

    def reinitialize(self):
        # Reinitialize ourself.  For now, just clear route parameters.
        self.route_params = {}


class HobokenApplication(object):
    SUPPORTED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")

    def __init__(self, name):
        self.name = name

        # Routes array. We split this by method, both for speed and simplicity.
        # Format: List of tuples of the form (matcher, function)
        self.routes = {}

        for m in self.SUPPORTED_METHODS:
            self.routes[m] = []

    def add_route(self, method, match, func):
        # Methods are uppercase.
        method = method.upper()

        # Check for valid method.
        if not method in self.SUPPORTED_METHODS:
            raise HobokenException("Invalid method type given: %s" % (method,))

        # Determine match type.
        if isinstance(match, BaseStringType):
            # Param/splat style.  We need to extract the splats, the named
            # parameters, and then create a regex to match it.
            #
            # The general rules are as follows:
            #  - Block parameters like :block match one path segment -
            #    i.e. until the next "/", special character, or end-of-
            #    string.  Note that blocks must match at least one
            #    character.
            #  - Splats match anything, but always match non-greedily.
            #    Splats can also match the empty string (i.e. nothing).
            #
            # So, we convert to a regex in the following way:
            #  - Blocks are converted like this:
            #      blah:block --> r"blah([^/?#]+)"
            #  - Splats are converted like this:
            #      blah*blah  --> r"blah(.*?)blah"

            keys = []

            def convert_match(match):
                if match.group(0) == '*':
                    keys.append("splat")
                    return r"(.*?)"
                else:
                    keys.append(match.group(0)[1:])
                    return r"([^/?#]+)"

            # First we encode special characters.  The helper function will
            # return a regex that matches that character and any modifications.
            def encode_character(char):
                if char == ' ':
                    return "(?: |" + encode_character("+") + ")"
                else:
                    encoded = urllib.quote(char)

                    # If the encoded version is unchanged, then we match both
                    # the bare version, along with the encoded version.
                    if encoded == char:
                        encoded = "(?:" + re.escape(char) + "|" + re.escape("%" + hex(ord(char))[2:]) + ")"

                    return encoded

            # Encode everything that's not in the set:
            #   [?%\/:*] + all alphanumeric characters + underscore.
            encoded_match = re.sub(r"[^?%\\/:*\w]", encode_character, match)

            # Now, replace parameters or splats with their matching regex.
            match_regex = re.sub(r"((:\w+)|\*)", convert_match, encoded_match)

            # Done - add the route.
            self.routes[method].append((RegexMatcher(match_regex, keys), func))

        elif isinstance(match, RegexType):
            # match is a regex, so we just add it as-is.
            self.routes[method].append((RegexMatcher(match), func))

        elif hasattr(match, "match") and iscallable(getattr(match, "match")):
            # Don't know what type it is, but it has a callable "match"
            # attribute, so we use that.
            self.routes[method].append((match, func))

        else:
            # Unknown type!
            raise InvalidMatchTypeException("Unknown type: %r" % (match,))

    def _decorate_and_route(self, method, match):
        def internal_decorator(func):
            self.add_route(method, match, func)
            return func
        return internal_decorator

    def get(self, match):
        return self._decorate_and_route("GET", match)

    def post(self, match):
        return self._decorate_and_route("POST", match)

    def put(self, match):
        return self._decorate_and_route("PUT", match)

    def delete(self, match):
        return self._decorate_and_route("DELETE", match)

    def head(self, match):
        return self._decorate_and_route("HEAD", match)

    def options(self, match):
        return self._decorate_and_route("OPTIONS", match)

    def patch(self, match):
        return self._decorate_and_route("PATCH", match)

    def wsgi_entrypoint(self, environ, start_response):
        # Create our request object.
        req = WebRequest(environ)

        # Check for valid method.
        if req.method not in self.SUPPORTED_METHODS:
            # Send "invalid method" exception.
            exc = HTTPMethodNotAllowed(location=environ.path)
            resp = req.get_response(exc)
            return resp(environ, start_response)

        # Create response.
        resp = Response()

        # For each route of the specified type, try to match it.
        matched = False
        for matcher, func in self.routes[req.method]:
            if matcher.match(req):
                matched = True

                try:
                    ret = func(req, resp)

                    # If we have a non-None return value, we set the body of
                    # the response to this value.
                    if ret is not None:
                        resp.body = ret
                except ContinueRoutingException:
                    # Reinitialize the request, which clears our route params.
                    matched = False
                    req.reinitialize()

                except HaltRoutingException:
                    # TODO: Halt routing.
                    pass

                else:
                    # The 'else' clause is executed when NO exception has been
                    # raised.  This signifies that all has gone right, and thus
                    # we should continue to process "after()" calls, and so on.

                    # TODO: Fill me in.
                    pass

                # Stop processing this request - we're done.
                break

        if not matched:
            # Return a 404 request.
            exc = HTTPNotFound(location=req.path)
            resp = req.get_response(exc)

        return resp(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_entrypoint(environ, start_response)
