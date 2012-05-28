

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


class NotDecoratedException(HobokenException):
    """
    Exception raised when trying to use conditions, or other decorators, on a
    function that hasn't been decorated with a route.
    """
    pass
