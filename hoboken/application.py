import re
from functools import wraps

from webob import Request, Response

from .exceptions import *


# TODO: Move to utils module?
REGEX_TYPE = type(re.compile(""))


class HobokenApplication(object):
    def __init__(self, name):
        self.name = name
        self.routes = []

    def _decorate_function(self, func):
        """
        Decorate the given function to be a WSGI application, and add the
        necessary logic for our application.
        """
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

    def _ensure_decorated(self, func):
        """
        Ensure that the given function has been decorated with
        _decorate_function.
        """

        # Don't double-decorate a function.
        if func.func_dict.get("hoboken_wrapped", False):
            return func

        # Not decorated, so mark it as decorated and do so.
        func.func_dict['hoboken_wrapped'] = True
        return self._decorate_function(func)

    def _make_decorator(self, method, match):
        if isinstance(match, basestring):
            # Parse "match" to determine if splat-style or param-style.
            pass
        elif isinstance(match, REGEX_TYPE):
            # match is a regex, so we just add it as-is.
            pass
        elif hasattr(match, "match") and callable(getattr(match, "match")):
            # Don't know what type it is, but it has a callable "match"
            # attribute, so we use that.
            pass
        else:
            # Unknown type!
            raise InvalidMatchTypeException("Unknown type: %r" % (match,))

    def get(self, match):
        return _make_decorator("GET", match)

    def post(self, match):
        return _make_decorator("POST", match)
