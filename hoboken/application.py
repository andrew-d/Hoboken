from functools import wraps

from webob import Request, Response

from .exceptions import *
from .compat import *


def _is_decorated(func):
    """
    Check if the given function is decorated with an application decorator.
    """
    return func.func_dict.get("hoboken_wrapped", False)


def _check_decorated(func):
    """
    Check if the given function is decorated with an application decorator,
    and throw an error if not.
    """

    if not _is_decorated(func):
        raise NotDecoratedException("Function %r not decorated!" % (func,))


class BasicMatcher(object):
    """
    Basic matcher - just checks if the path matches exactly.
    """
    def __init__(self, path):
        self.path = path

    def match(self, request):
        return self.path == request.path


class RegexMatcher(object):
    """
    This class matches a URL using a provided regex.
    """

    def __init__(self, re):
        self.re = re

    def match(self, request):
        if self.re.match(request.path):
            return True
        else:
            return False

        # TODO: send matched groups to the function


class HobokenApplication(object):
    def __init__(self, name):
        self.name = name
        self.routes = []        # Format: (method, matcher, function)

        # TODO: Split routes into per-method routes, to speed up?

    def _decorate_function(self, func):
        """
        Decorate the given function to be a WSGI application, and add the
        necessary logic for our application.
        """

        # Mark the function as decorated.
        func.func_dict['hoboken_wrapped'] = True

        # This decorator makes the function a WSGI application.
        @wraps(func)
        def wrapper(environ, start_response, *args, **kwargs):
            # Create our WebOb request.
            req = Request(environ)

            # Call wrapped function.
            retval = func(req, *args, **kwargs)

            # Make a WSGI response.
            resp = Response(body=retval)

            # Return our actual response.
            return resp(environ, start_response)

        return wrapper

    def _make_decorator(self, method, match):
        # TODO: decorate me!
        func = method

        if isinstance(match, BaseStringType):
            # Parse "match" to determine if splat-style, param-style, or bare.
            if match.find(":") != -1 or match.find("*") != -1:
                # Param/splat style
                pass
            else:
                # Bare.  Create matcher, return it.
                self.routes.append((method, BasicMatcher(match), func))
        elif isinstance(match, RegexType):
            # match is a regex, so we just add it as-is.
            self.routes.append((method, RegexMatcher(match), func))
        elif hasattr(match, "match") and iscallable(getattr(match, "match")):
            # Don't know what type it is, but it has a callable "match"
            # attribute, so we use that.
            self.routes.append((method, match, func))
        else:
            # Unknown type!
            raise InvalidMatchTypeException("Unknown type: %r" % (match,))

    def get(self, match):
        return _make_decorator("GET", match)

    def post(self, match):
        return _make_decorator("POST", match)
