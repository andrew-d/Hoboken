import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join('..')))

import hoboken
import hoboken.conditions
from webob import Request

# Helper function.  Calls the given application, returns a tuple of
# (status_int, body)
def call_app(app, path="/", method="GET"):
    req = Request.blank(path)
    req.method = method
    resp = req.get_response(app)
    return resp.status_int, resp.body


def body_func(req, resp):
    return "request body"
