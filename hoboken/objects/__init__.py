# This imports six from the above package, for compatibility.
from .. import six

# Import our request / response.
from .request import WSGIFullRequest
# from .response import WSGIFullResponse
WSGIFullResponse = object
