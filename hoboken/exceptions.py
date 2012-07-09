

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


class HaltRoutingException(HobokenUserException):
    """
    This exception signals that Hoboken should stop routing the current
    request.  NOTE: after() calls ARE called.
    """
    def __init__(self, *args, **kwargs):
        self.status_code = kwargs.pop('status_code', 0)
        self.body = kwargs.pop('body', None)
        super(HaltRoutingException, self).__init__(*args, **kwargs)


class RedirectException(HobokenUserException):
    """
    This exception signals a redirect to another location.  Unless the
    'redirect_type' argument is given, defaults to a 302 redirect.
    """
    def __init__(self, *args, **kwargs):
        self.redirect_type = kwargs.get("redirect_type", 302)
        super(RedirectException, self).__init__(*args, **kwargs)
