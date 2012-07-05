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


# TODO: move this to another file.
def condition(condition_func):
    def internal_decorator(func):
        # Either call the add_condition() func, or add this condition to the
        # list of conditions on the function.
        if 'hoboken.add_condition' in func.func_dict:
            func.func_dict['hoboken.add_condition'](condition_func)
        elif 'hoboken.conditions' in func.func_dict:
            func.func_dict['hoboken.conditions'].append(condition_func)
        else:
            func.func_dict['hoboken.conditions'] = [condition_func]

        return func

    return internal_decorator


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

        # Before and after filter arrays.  These are in the same format as
        # the routes[] array, above.
        self.before_filters = []
        self.after_filters = []

        # Create logger.
        self.logger = logging.getLogger("hoboken.applications." + self.name)

        # Configure logger.
        formatter = logging.Formatter('[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            handler.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.WARN)
            handler.setLevel(logging.WARN)

    def _encode_character(self, char):
        """
        This function will encode a given character as a regex that will match
        it in either regular or encoded form.
        """
        encode_char = lambda c: re.escape("%" + hex(ord(c))[2:])

        # Was trying to use urllib.quote here, but it tries to encode too much for
        # my liking.  Just using a regex.
        if re.match(r"[;/?:@&=+$,\[\]]", char):
            encoded = encode_char(char)
        else:
            encoded = char

        # If the encoded version is unchanged, then we match both
        # the bare version, along with the encoded version.
        if encoded == char:
            encoded = "(?:" + re.escape(char) + "|" + encode_char(char) + ")"

        # Specifically for the space charcter, we match everything, and also plus characters.
        if char == ' ':
            encoded = "(?:" + encoded + "|" + self._encode_character("+") + ")"

        return encoded

    def _make_route(self, match, func):
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

            # Wrapper function that simply passes through to encode_character() with the
            # match's content.
            def encode_character_wrapper(match):
                return self._encode_character(match.group(0))

            # Encode everything that's not in the set:
            #   [?%\/:*] + all alphanumeric characters + underscore.
            encoded_match = re.sub(r"[^?%\\/:*\w]", encode_character_wrapper, match)

            # Now, replace parameters or splats with their matching regex.
            match_regex = re.sub(r"((:\w+)|\*)", convert_match, encoded_match)

            # Done - add the route.
            return (RegexMatcher(match_regex, keys), [], func)

        elif isinstance(match, RegexType):
            # match is a regex, so we extract any named groups.
            keys = [None] * match.groups
            for name, index in match.groupindex.iteritems():
                keys[index] = name

            # Append the route with these keys.
            return (RegexMatcher(match, keys), [], func)

        elif hasattr(match, "match") and iscallable(getattr(match, "match")):
            # Don't know what type it is, but it has a callable "match"
            # attribute, so we use that.
            return (match, [], func)

        else:
            # Unknown type!
            raise InvalidMatchTypeException("Unknown type: %r" % (match,))

    def add_route(self, method, match, func):
        # Methods are uppercase.
        method = method.upper()

        # Check for valid method.
        if not method in self.SUPPORTED_METHODS:
            raise HobokenException("Invalid method type given: %s" % (method,))

        route_tuple = self._make_route(match, func)
        self.routes[method].append(route_tuple)

    def find_route(self, method, func):
        for t in self.routes[method]:
            if t[2] == func:
                return t

        return None

    def _decorate_and_route(self, method, match):
        def internal_decorator(func):
            # This allows us to add conditions!
            def add_condition(condition_func):
                route_tuple = self.find_route(method, func)
                route_tuple[1].append(condition_func)
                print "Added condition {0} for func {1}/{2}:".format(
                    repr(condition_func), str(method), repr(func))

            # Add the route.
            self.add_route(method, match, func)

            # Add each of the existing conditions.
            if 'hoboken.conditions' in func.func_dict:
                for c in func.func_dict['hoboken.conditions']:
                    add_condition(c)

                del func.func_dict['hoboken.conditions']

            # Mark this function as a route.
            func.func_dict['hoboken.route'] = True

            # Add a function to add future conditions. This is so the order
            # of conditions being added doesn't matter.
            func.func_dict['hoboken.add_condition'] = add_condition
            return func
        return internal_decorator

    def add_before_filter(self, match, func):
        filter_tuple = self._make_route(match, func)
        self.before_filters.append(filter_tuple)

    def before(self, match=None):
        # If the match isn't provided, we match anything.
        if match is None:
            match = re.compile(".*")

        def internal_decorator(func):
            self.add_before_filter(match, func)
            return func
        return internal_decorator

    def add_after_filter(self, match, func):
        filter_tuple = self._make_route(match, func)
        self.after_filters.append(filter_tuple)

    def after(self, match=None):
        # If the match isn't provided, we match anything.
        if match is None:
            match = re.compile(".*")

        def internal_decorator(func):
            self.add_after_filter(match, func)
            return func
        return internal_decorator

    def _process_route(self, req, resp, route_tuple):
        matcher, conditions, func = route_tuple

        if not matcher.match(req):
            return False

        try:
            for cond in conditions:
                if not cond(req):
                    raise ContinueRoutingException

            ret = func(req, resp)
            if ret is not None:
                resp.body = ret

        except ContinueRoutingException:
            req.reinitialize()
            return False

        return True

    def wsgi_entrypoint(self, environ, start_response):
        # Create our request object.
        req = WebRequest(environ)
        self.logger.debug("%s %s", req.method, req.url)

        # Check for valid method.
        if req.method not in self.SUPPORTED_METHODS:
            self.logger.warn("Called with invalid method: %r", req.method)

            # Send "invalid method" exception.
            exc = HTTPMethodNotAllowed(location=req.path)
            resp = req.get_response(exc)
            return resp(environ, start_response)

        # Create response.
        resp = Response()

        matched = False
        try:
            for filt_tuple in self.before_filters:
                # Call this filter.
                self._process_route(req, resp, filt_tuple)

            # For each route of the specified type, try to match it.
            for route_tuple in self.routes[req.method]:
                if self._process_route(req, resp, route_tuple):
                    matched = True
                    break

        except HaltRoutingException as halt:
            # TODO: check if the exception specifies a status code or
            # body, and then set these on the request
            pass

        except Exception as e:
            # TODO: Output a 500 error.
            # Also, check if the exception has other information attached,
            # like a code/body.
            # TODO: Handle other HTTPExceptions from webob?
            pass

        finally:
            # Call our after filters
            for filt_tuple in self.after_filters:
                self._process_route(req, resp, filt_tuple)

        if not matched:
            resp = self.on_route_missing(req)

        return resp(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_entrypoint(environ, start_response)

    def on_route_missing(self, req):
        """
        This function is called when a route to handle a request is not found.
        It should return a Response that will then be sent to the requestor.
        Override this function to provide custom not-found logic.
        """
        # By default, return a 404 request.
        exc = HTTPNotFound(location=req.path)
        resp = req.get_response(exc)
        return resp

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

    def __str__(self):
        """
        Some help for debugging: repr(app) will get a summary of the app and
        it's defined before/after/routes.
        """

        body = []
        body.append("Application {0} (Debug: {1})".format(self.name, self.debug))
        body.append("")

        def dump_filter_array(arr):
            body.append("=" * 79)
            body.append("Function        Match                     Conditions")
            body.append("-" * 79)
            for match, cond, func in arr:
                conds = ", ".join([f.func_name for f in cond])
                body.append("{0:<15} {1:<25} {2:<35}".format(func.func_name, str(match), conds))

        def dump_route_array(arr):
            body.append("=" * 79)
            body.append("Method  Function        Match                     Conditions")
            body.append("-" * 79)
            for method in self.routes:
                for match, cond, func in self.routes[method]:
                    conds = ", ".join([f.func_name for f in cond])
                    body.append("{0:<7} {1:<15} {2:<25} {3:<28}".format(method, func.func_name, str(match), conds))

        body.append("BEFORE FILTERS")
        dump_filter_array(self.before_filters)
        body.append("")

        body.append("ROUTES")
        dump_route_array(self.before_filters)
        body.append("")

        body.append("AFTER FILTERS")
        dump_filter_array(self.after_filters)
        body.append("")

        return '\n'.join(body)

    def __repr__(self):
        return "HobokenApplication(name={!r}, debug={!r})".format(self.name, self.debug)




# TODO:
# def hoboken_wrapper(func):
#     def add_condition(condition):
#         print "Adding condition: %r" % (condition,)
# 
#     if 'hoboken.conditions' in func.func_dict:
#         for c in func.func_dict['hoboken.conditions']:
#             add_condition(c)
# 
#         del func.func_dict['hoboken.conditions']
# 
#     func.func_dict['hoboken.add_condition'] = add_condition
#     func.func_dict['hoboken.wrapped'] = True
