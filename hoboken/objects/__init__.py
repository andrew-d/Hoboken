# Import our request / response.
from .request import WSGIFullRequest
from .response import WSGIFullResponse

# Set the response class.  This is done here to avoid circular imports.
WSGIFullRequest.ResponseClass = WSGIFullResponse
