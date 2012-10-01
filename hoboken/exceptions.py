

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
    This exception type is the base class for all exceptions that take
    arguments to be set on the Response() object.  It simply stores them for
    use by the application.
    """
    def __init__(self, code, body, headers):
        self.code = code
        self.body = body
        self.headers = headers
        super(HaltRoutingException, self).__init__()

