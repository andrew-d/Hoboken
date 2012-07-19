

class HobokenException(Exception):
    """Base class for all Hoboken exceptions."""
    pass


class InvalidMatchTypeException(HobokenException):
    """
    Invalid matcher type given for a function.  Valid types are:
      - A string, in either splat ("/blah/*/blah") or named-parameter
        ("/blah/:param") format.
      - A regex object (e.g. re.compile("/blah/(.+)"))
      - A custom object that provides a match() callable.
    """
    pass


class RouteExistsException(HobokenException):
    """
    Exception raised when trying to set multiple route decorators on a function.
    """
    pass


class HobokenUserException(HobokenException):
    """Base class for all user-raise-able exceptions."""
    pass


class ContinueRoutingException(HobokenUserException):
    """
    This exception signals that Hoboken should continue routing the current
    request.  The current route is ignored, and the next one is tried.
    """
    pass


class HobokenResponseException(HobokenUserException):
    """
    This exception type is the base class for all exceptions that take
    arguments to be set on the Response() object.  It simply stores them for
    use by the application.
    """
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        super(HobokenResponseException, self).__init__()


class HaltRoutingException(HobokenResponseException):
    """
    This exception signals that Hoboken should stop routing the current
    request.  NOTE: after() calls ARE called.
    """
    def __init__(self, *args, **kwargs):
        super(HaltRoutingException, self).__init__(*args, **kwargs)


class RedirectException(HobokenResponseException):
    """
    This exception signals a redirect to another location.  Unless the
    'redirect_type' argument is given, defaults to a 302 redirect.
    """
    def __init__(self, *args, **kwargs):
        # Check if we're given one of the status codes.  If not, set it.
        if 'status' in kwargs:
            code = kwargs.pop('status')
        elif 'status_code' in kwargs:
            code = kwargs.pop('status_code')
        elif 'status_int' in kwargs:
            code = kwargs.pop('status_int')
        else:
            code = 302

        # Set the status, now that we have it.
        kwargs['status'] = code
        super(RedirectException, self).__init__(*args, **kwargs)

