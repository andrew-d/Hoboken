from __future__ import with_statement, absolute_import

from .application import halt
import datetime

def _not_modified(req, resp, *args, **kwargs):
    """
    Helper function.
    halt()'s with a 304 Not Modified code.
    """
    halt(status_code=304, *args, **kwargs)


def check_if_modified(req, resp, date):
    """
    This function will check if a given request's if-modified-since header
    is set, and, if so, will check it against the date provided.  If the
    request specifies an equivalent or newer resource, this function will call
    halt() to abort the current request with a 304 Not Modified status.
    """
    if req.last_modified >= date:
        _not_modified(req, resp, last_modified=date)
    else:
        resp.last_modified = date


def check_etag(req, resp, etag, weak=False):
    """
    As per check_if_modified(), except checks the ETag header instead.
    """
    # The logic here is as follows:
    #  - If the request specifies no If-None-Match, return
    #  - If the header exists, check and potentially halt().
    #  - Sets the ETag header on the response.
    if req.if_none_match == etag:
        _not_modified(req, resp, etag=(etag, not weak))
    else:
        resp.etag = (etag, not weak)

