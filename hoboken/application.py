# Future-proofing
from __future__ import with_statement, absolute_import, print_function

# Stdlib dependencies
import os
import sys
import re
import logging
import traceback
from datetime import datetime
try:
    import threading
except:                     # pragma: no cover
    import dummy_threading as threading

# In-package dependencies
from hoboken.exceptions import *
from hoboken.matchers import *
from hoboken.objects import WSGIFullRequest as Request
from hoboken.objects import WSGIFullResponse as Response
from hoboken.config import ConfigProperty, ConfigDict
from hoboken.log import DebugLogger, InjectingFilter

# Compatibility.
from hoboken.six import (with_metaclass, text_type, binary_type, string_types,
                         callable, iteritems)


# Get a logger.
logger = logging.getLogger(__name__)


def get_func_attr(func, attr, default=None, delete=False):
    if delete:
        return func.__dict__.pop(attr, default)
    else:
        return func.__dict__.get(attr, default)


def set_func_attr(func, attr, value):
    func.__dict__[attr] = value


def condition(condition_func):
    def internal_decorator(func):
        # Either call the add_condition() func, or add this condition to the
        # list of conditions on the function.
        add_condition = get_func_attr(func, 'hoboken.add_condition')
        if add_condition is not None:
            add_condition(condition_func)
            return func

        conditions_arr = get_func_attr(func, 'hoboken.conditions', default=[])
        conditions_arr.append(condition_func)
        set_func_attr(func, 'hoboken.conditions', conditions_arr)

        return func

    return internal_decorator


def halt(code=None, body=None, headers=None):
    """
    This function halts routing, and returns immediately.  If the code, body
    or headers parameters are given, this will set those values on the
    response.
    """
    raise HaltRoutingException(code, body, headers)


def pass_route():
    """
    This function signals that we should stop processing the current route and
    continue trying to match routes.  If no more routes are found, a 404 error
    will be returned.
    """
    raise ContinueRoutingException()


class Route(object):
    """
    This class is an abstraction around a URL route.  It encapsulates:
      - The request method.
      - Any conditions defined for the route.
      - A matcher that determines if the route matches a request, and also
        returns any parameters from the request.
      - And finally, the route function itself.
    """
    def __init__(self, matcher, func, conditions=None):
        self.matcher = matcher
        self.func = func
        self.conditions = conditions or []

        self._method = None

    @property
    def method(self):
        return self._method

    @method.setter
    def method(self, val):
        self._method = val.upper()

    def add_condition(self, condition):
        self.conditions.append(condition)

    def reverse(self, *args, **kwargs):
        return self.matcher.reverse(args, kwargs)

    def __call__(self, request, response):
        """
        Call this route.  This function will return True or False, depending on
        whether the route matched and was processed.  It will also catch any
        ContinueRoutingExceptions and return False.
        """
        # self.logger.debug("Processing route: {0}".format(repr(route_tuple)))

        # Reset the parameters in the request before each match,
        request.urlargs = ()
        request.urlvars = {}

        # Do the match.
        does_match, args, kwargs = self.matcher.match(request)
        if not does_match:
            return False, None
        else:
            request.urlargs = tuple(args)
            request.urlvars = kwargs

        try:
            for cond in self.conditions:
                if not cond(request):
                    raise ContinueRoutingException

            # We remove the optional "_captures" kwarg, if it exists.
            kwargs.pop('_captures', None)
            ret = self.func(*args, **kwargs)

        except ContinueRoutingException:
            return False, None

        return True, ret


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

        # Grab the SUPPORTED_METHODS constant and use this to dynamically add
        # methods.
        for method in attrs.get('SUPPORTED_METHODS', []):
            new_func = lambda_factory(method)
            new_func.__name__ = method.lower()
            attrs[method.lower()] = new_func

        # Call the base's __new__ now with our modified attributes.
        return super(HobokenMetaclass, klass).__new__(klass, name, bases,
                                                      attrs)


def is_route(func):
    """
    This function will return a boolean specifying whether a given function is
    a Hoboken route.
    """
    return get_func_attr(func, 'hoboken.route', default=False)


class SimpleNamespace(object):
    """
    This is a basic, empty object with a usable __repr__.

    NOTE: taken from the example code for types.SimpleNamespace in Python 3.3.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))


class HobokenBaseApplication(with_metaclass(HobokenMetaclass)):
    # These are the supported HTTP methods.  They can be overridden in
    # subclasses to add additional methods (e.g. "TRACE", "CONNECT", etc.)
    SUPPORTED_METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS",
                         "HEAD")

    DEFAULT_CONFIG = {
        'DEBUG': False,
        'APPLICATION_FILE': None,
        'SERIALIZE_REQUESTS': False,
    }

    # The application's debug setting.
    debug = ConfigProperty('DEBUG')

    def __init__(self, name, config={}):
        self.name = name

        # Set up threadlocal storage.  We use this so we can process multiple
        # requests at the same time from one app.
        # NOTE: this needs to be done before logging, since InjectingFilter
        # will inject the request/response objects into a log message.
        self._locals = threading.local()
        self._locals.request = None
        self._locals.response = None
        self._locals.vars = SimpleNamespace()

        # If we're missing the root dir, we try and determine them here.
        app_file = config.get('APPLICATION_FILE')
        if app_file is None:
            import __main__

            # Get the file name if it exists.  It won't in, for example, the
            # interactive console.
            if hasattr(__main__, "__file__"):
                app_file = os.path.abspath(__main__.__file__)
            else:               # pragma: no cover
                app_file = os.path.abspath(".")

        # Given the application file, get the root directory.
        root_dir = config.get('ROOT_DIRECTORY')
        if root_dir is None:
            root_dir = os.path.dirname(app_file)

        # Create our config, and set values in it.
        self.config = ConfigDict(root_dir, defaults=self.DEFAULT_CONFIG)
        self.config.update(config)

        # Set our heuristically-determined things.
        self.config['APPLICATION_FILE'] = app_file
        self.config['ROOT_DIRECTORY'] = root_dir

        # Set other directory values.
        self.config.setdefault('VIEWS_DIRECTORY', os.path.join(
            self.config['ROOT_DIRECTORY'],
            "views"
        ))
        self.config.setdefault('STATIC_DIRECTORY', os.path.join(
            self.config['ROOT_DIRECTORY'],
            "static"
        ))

        # Routes array. We split this by method, both for speed and simplicity.
        self.routes = {}
        # TODO: Might be worth having a reverse-mapping array, so we can turn a
        # function into a route (e.g. for URL generation, and so on).

        for m in self.SUPPORTED_METHODS:
            self.routes[m] = []

        # Before and after filter arrays.  Note that these are also Routes
        self.before_filters = []
        self.after_filters = []

        # Create logger.
        self.logger = self.create_logger()

        # Create a lock which we might use to serialize requests.  Originally,
        # this was only created if the appropriate config value was set, but
        # this caused problems if the config value was then set after the
        # application was created.
        self.lock = threading.Lock()

        # Call other __init__ functions - this is needed for mixins to work.
        super(HobokenBaseApplication, self).__init__()

        # Done initialization.
        self.logger.info("Application initialized")

    def create_logger(self):
        logger = logging.getLogger('hoboken.applications.' + self.name)

        # Override the __class__ of the logger so we can deal with the debug
        # setting.
        logger.app = self
        logger.__class__ = DebugLogger

        # Add a filter that will store the request and response object on each
        # log record.
        logger.addFilter(InjectingFilter(self))

        return logger

    @property
    def request(self):
        return self._locals.__dict__.get('request')

    @request.setter
    def request(self, val):
        self._locals.request = val

    @request.deleter
    def request(self):
        self._locals.request = None

    @property
    def response(self):
        return self._locals.__dict__.get('response')

    @response.setter
    def response(self, val):
        self._locals.response = val

    @response.deleter
    def response(self):
        self._locals.response = None

    @property
    def g(self):
        v = self._locals.__dict__.get('vars')
        if v is None:       # pragma: no cover
            v = self._locals.vars = SimpleNamespace()
        return v

    @g.deleter
    def g(self):
        self._locals.vars = SimpleNamespace()

    def delegate(self, app, catch_exceptions=False):
        """
        Delegates processing of the current request to another WSGI
        application.  Will set the current response to the response that was
        recieved from the other application.
        """
        if self.request is None:
            return False

        # Make the request on the subapp.
        resp = self.request.get_response(app, catch_exc_info=catch_exceptions)

        # Set our response.
        self.response = resp
        return True

    def _make_route(self, match, func):
        if isinstance(match, string_types):
            matcher = HobokenRouteMatcher(match)
        elif isinstance(match, RegexType):
            # match is a regex, so we extract any named groups.
            keys = [None] * match.groups
            types = [False] * match.groups
            for name, index in iteritems(match.groupindex):
                types[index - 1] = True
                keys[index - 1] = name

            # Append the route with these keys.
            matcher = RegexMatcher(match, types, keys)

        elif hasattr(match, "match") and callable(getattr(match, "match")):
            # Don't know what type it is, but it has a callable "match"
            # attribute, so we use that.
            matcher = match

        else:
            # Unknown type!
            raise InvalidMatchTypeException("Unknown type: %r" % (match,))

        return Route(matcher, func)

    def add_route(self, method, match, func):
        # Methods are uppercase.
        method = method.upper()

        # Check for valid method.
        if not method in self.SUPPORTED_METHODS:
            raise HobokenException("Invalid method type given: %s" % (method,))

        route = self._make_route(match, func)
        route.method = method
        self.routes[method].append(route)

    def find_route_with_method(self, method, func):
        for route in self.routes[method]:
            if route.func == func:
                return route

        return None

    def find_route(self, func):
        for method in self.SUPPORTED_METHODS:
            route = self.find_route_with_method(method, func)
            if route:
                return route

        return None

    def url_for(self, function, *args, **kwargs):
        route = self.find_route(function)
        if route is None:
            return None

        path = route.reverse(*args, **kwargs)
        return path

    def redirect(self, location, code=None, body=None, headers=None):
        """
        This is a helper function for redirection.
        """

        # If a code is specified, we take that.
        if code is None:
            # If no code, we send a 303 if it's supported and we aren't already
            # using GET.
            if (self.request.http_version == b'HTTP/1.1' and
                    self.request.method != 'GET'):
                code = 303
            else:
                code = 302

        # Ensure we have the 'headers' dict.
        headers = headers or {}

        # Set the 'location' argument, which sets the 'Location' header.
        headers['Location'] = location

        # Halt routing with these parameters.
        halt(code=code, body=body, headers=headers)

    def _decorate_and_route(self, method, match):
        def internal_decorator(func):
            # We only allow one route for each function.
            if is_route(func):
                logger.error("Function %s is already a route", func.__name__)
                raise RouteExistsException()

            # This allows us to add conditions!
            def add_condition(condition_func):
                route = self.find_route(func)
                route.add_condition(condition_func)
                self.logger.debug("Added condition '%s' for func %s/%s",
                                  condition_func.__name__,
                                  str(method),
                                  func.__name__)

            # Add the route.
            self.add_route(method, match, func)

            # Add each of the existing conditions.
            conditions = get_func_attr(func, 'hoboken.conditions', default=[],
                                       delete=True)
            for c in conditions:
                add_condition(c)

            # Mark this function as a route.
            set_func_attr(func, 'hoboken.route', True)

            # Add a function to add future conditions. This is so the order
            # of conditions being added doesn't matter.
            set_func_attr(func, 'hoboken.add_condition', add_condition)
            return func

        return internal_decorator

    def add_before_filter(self, match, func):
        filter_tuple = self._make_route(match, func)
        self.before_filters.append(filter_tuple)

    def before(self, match=None):
        # If the match isn't provided, we match anything.
        if match is None:
            match = re.compile(b".*")

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
            match = re.compile(b".*")

        def internal_decorator(func):
            self.add_after_filter(match, func)
            return func
        return internal_decorator

    def on_returned_body(self, request, resp, value):
        """
        This function is used to turn a value that's been returned from a
        route function into the request body.  Override this in a subclass
        to customize how values are returned.
        """
        if isinstance(value, text_type):
            resp.text = value
        elif isinstance(value, binary_type):
            resp.body = value
        else:
            logger.error("Unknown return type: %r", type(value))
            raise ValueError("Unknown return type: {0!r}".format(type(value)))

    def wsgi_entrypoint(self, environ, start_response):
        # Flag stating whether we've acquired our lock.  Defaults to False,
        # since we (by default) do not serialize requests.
        locked = False

        try:
            if self.config['SERIALIZE_REQUESTS']:
                # Acquire, then set our flag.  Note that order matters here,
                # since we only want to set the 'locked' flag when it is safe
                # to unlock (see below for more notes).
                self.lock.acquire()
                locked = True

            # Create our request object.
            self.request = Request(environ)

            # Create an empty response.
            self.response = Response()

            # Create our variables object.
            self._locals.vars = SimpleNamespace()

            # Set default values on the response.
            self._prepare_response()

            # Actually handle this request.
            self._handle_request()

            # Finally, given our response, we finish the WSGI request.
            return self.response(environ, start_response)
        finally:
            # Note that we don't automatically release, since there might be
            # an error with accessing self.config, above, and so we might not
            # have acquired the lock.
            if locked:
                self.lock.release()

            # After each request, we remove the request and response objects.
            del self.request
            del self.response

            # We also reset our request config.
            del self.g

    def _prepare_response(self):
        # We default to setting the current (UTC) date on the response.
        if hasattr(self.response, 'date'):
            self.response.date = datetime.utcnow()

    def _run_routes(self, method):
        # Since these are thread-locals, we grab them as locals.
        request = self.request
        response = self.response

        # For each route of the specified type, try to match it.
        for route in self.routes[method]:
            matches, ret = route(request, response)
            if ret is not None:
                self.on_returned_body(request, response, ret)

            if matches:
                return True

        return False

    def _handle_request(self):
        # Since these are thread-locals, we grab them as locals.
        request = self.request
        response = self.response
        self.logger.debug("Handling: %s %s", request.method, request.url)

        # Check for valid method.
        # TODO: Should this call our after filters?
        if request.method not in self.SUPPORTED_METHODS:
            self.logger.warn("Called with invalid method: %s", request.method)

            # TODO: hook.

            # Send "invalid method" exception.
            response.status_int = 405
            return

        matched = False
        try:
            # Call before filters.
            for filter in self.before_filters:
                filter(request, response)

            # For each route of the specified type, try to match it.
            matched = self._run_routes(request.method)

            # We special-case the HEAD method to fallback to GET.
            if request.method == 'HEAD' and not matched:
                # Run our routes against the 'GET' method.
                matched = self._run_routes('GET')

        except HaltRoutingException as ex:
            # Set the various parameters.
            if ex.code is not None:
                response.status_int = ex.code

            if ex.body is not None:
                # We pass the body through to on_returned_body.
                self.on_returned_body(request, response, ex.body)

            if ex.headers is not None:
                # Set each header.
                for header, value in iteritems(ex.headers):
                    # Set this header.
                    response.headers[header] = value

            # Must set this, or we get clobbered by the 404 handler.
            matched = True

        except Exception as e:
            # Also, check if the exception has other information attached,
            # like a code/body.
            self.on_exception(e)

            # Must set this, or we get clobbered by the 404 handler.
            matched = True

        finally:
            # Call our after filters
            for route in self.after_filters:
                route(request, response)

        if not matched:
            self.on_route_missing()

    def __call__(self, environ, start_response):
        return self.wsgi_entrypoint(environ, start_response)

    def on_route_missing(self):
        """
        This function is called when a route to handle a request is not found.
        Override this function to provide custom not-found logic.
        """
        # By default, return a 404 request.
        self.response.status_int = 404

    def on_exception(self, exception):
        self.response.status_int = 500
        if self.config['DEBUG']:
            # Format the current traceback
            tb = traceback.format_exc()

            # Return the traceback as text.
            self.response.content_type = 'text/plain'
            if sys.version_info[0] >= 3:
                self.response.text = tb
            else:
                self.response.body = tb

            print(tb, file=sys.stderr)

    def test_server(self, port=8000):                   # pragma: no cover
        """
        This method lets you start a test server for development purposes.
        Note: There is deliberately no option to set the address to listen on.
              The server will always listen on 'localhost', and should never
              be used in production.
        """

        self.logger.info("Starting test server on port %d", port)

        from wsgiref.simple_server import make_server
        httpd = make_server('localhost', port, self)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            self.logger.info("Stopped test server due to keyboard interrupt")

    def __str__(self):
        """
        Some help for debugging: str(app) will get a summary of the app and
        it's defined before/after/routes.
        """

        body = []
        body.append("Application {0} (Debug: {1})".format(
            self.name,
            self.config['DEBUG']
        ))
        body.append("")

        def dump_filter_array(arr):
            body.append("=" * 79)
            body.append("Function        Match                     Conditions")
            body.append("-" * 79)
            for filter in arr:
                conds = ", ".join([f.__name__ for f in filter.conditions])
                body.append("{0:<15} {1:<25} {2:<35}".format(
                    filter.func.__name__, str(filter.match), conds
                ))

        def dump_route_array(arr):
            body.append("=" * 79)
            body.append(
                "Method  Function        Match                     Conditions"
            )
            body.append("-" * 79)
            for method in self.routes:
                for route in self.routes[method]:
                    conds = ", ".join([f.__name__ for f in route.conditions])
                    body.append("{0:<7} {1:<15} {2:<25} {3:<28}".format(
                        method,
                        route.func.__name__,
                        str(route.matcher),
                        conds
                    ))

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
        return "HobokenApplication(name={!r}, debug={!r})".format(
            self.name,
            self.config['DEBUG']
        )
