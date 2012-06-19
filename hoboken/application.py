# Future-proofing
from __future__ import with_statement, absolute_import

# Stdlib dependencies
import re
import urllib
import logging
#from functools import wraps

# External dependencies
from webob import Request, Response
from webob.exc import HTTPMethodNotAllowed, HTTPNotFound

# In-package dependencies
from .exceptions import *
from .matchers import *
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

        self.reinitialize()

    def reinitialize(self):
        # Reinitialize ourself.  For now, just clear route parameters.
        self.route_params = {}


class HobokenMetaclass(type):
    """
    This class does "black magic" to create an instance of HobokenApplication
    by dynamically adding methods to the class that handle each of the methods
    that are listed in SUPPORTED_METHODS.
    """

    def __new__(klass, name, bases, attrs):
        # This function gets around Python's scoping of lambdas.
        def lambda_factory(method):
            return lambda self, match: self._decorate_and_route(method, match)

        # Grab the SUPPORTED_METHODS constant and use this to dynamically add methods.
        for method in attrs['SUPPORTED_METHODS']:
            new_func = lambda_factory(method)
            new_func.__name__ = method.lower()
            attrs[method.lower()] = new_func

        # Call the base's __new__ now with our modified attributes.
        return super(HobokenMetaclass, klass).__new__(klass, name, bases, attrs)


class HobokenApplication(object):
    __metaclass__ = HobokenMetaclass

    # These are the supported HTTP methods.  They can be overridden in
    # subclasses to add additional methods (e.g. "TRACE", "CONNECT", etc.)
    SUPPORTED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD")

    def __init__(self, name, debug=False):
        self.name = name
        self.debug = debug

        # Routes array. We split this by method, both for speed and simplicity.
        # Format: List of tuples of the form (matcher, conditions, function)
        # Note: "conditions" is an array of conditions
        self.routes = {}

        for m in self.SUPPORTED_METHODS:
            self.routes[m] = []

        # Create logger.
        self.logger = logging.getLogger("hoboken.applications." + self.name)

        # Configure logger.
        formatter = logging.Formatter('[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)

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
                    # Otherwise, we just escape the quoted version (so our
                    # generated regex doesn't do funny things with it), and
                    # return that.
                    if encoded == char:
                        encoded = "(?:" + re.escape(char) + "|" + re.escape("%" + hex(ord(char))[2:]) + ")"
                    else:
                        encoded = re.escape(char)

                    return encoded

            # Wrapper function that simply passes through to encode_character() with the
            # match's content.
            def encode_character_wrapper(match):
                return encode_character(match.group(0))

            # Encode everything that's not in the set:
            #   [?%\/:*] + all alphanumeric characters + underscore.
            encoded_match = re.sub(r"[^?%\\/:*\w]", encode_character_wrapper, match)

            # Now, replace parameters or splats with their matching regex.
            match_regex = re.sub(r"((:\w+)|\*)", convert_match, encoded_match)

            # Done - add the route.
            self.routes[method].append((RegexMatcher(match_regex, keys), func))

        elif isinstance(match, RegexType):
            # match is a regex, so we extract any named groups.
            keys = [None] * match.groups
            for name, index in match.groupindex.iteritems():
                keys[index] = name

            # Append the route with these keys.
            self.routes[method].append((RegexMatcher(match, keys), func))

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

    def wsgi_entrypoint(self, environ, start_response):
        # Create our request object.
        req = WebRequest(environ)

        # Check for valid method.
        if req.method not in self.SUPPORTED_METHODS:
            # Send "invalid method" exception.
            exc = HTTPMethodNotAllowed(location=req.path)
            resp = req.get_response(exc)
            return resp(environ, start_response)

        # Create response.
        resp = Response()

        # TODO: Call 'before' filters.

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

    def test_server(self, port=8000):
        """
        This method lets you start a test server for development purposes.
        Note: There is deliberately no option to set the address to listen on.
              The server will always listen on 'localhost', and should never
              be used in production.
        """

        from wsgiref.simple_server import make_server
        httpd = make_server('localhost', port, self)
        httpd.serve_forever()
