from __future__ import with_statement, absolute_import

from .application import halt, redirect
import datetime


def check_last_modified(req, resp, date):
    """
    This function will check if one of a given request's last modified headers
    are set, and, if so, will check it against the date provided.  If the
    request specifies an equivalent or newer resource, this function will call
    halt() to abort the current request with a 304 Not Modified status.
    """
    resp.last_modified = date
    if req.if_none_match is not None:
        return

    if resp.status_int == 200 and req.if_modified_since is not None:
        if req.if_modified_since >= date:
            halt(status_code=304)

    if (resp.is_success or resp.status_int == 412 and
        req.if_unmodified_since is not None):
        if req.if_unmodified_since >= date:
            halt(status_code=412)


def check_etag(req, resp, etag, new_resource=None, weak=False):
    """
    As per check_if_modified(), except checks the ETag header instead.
    """
    resp.etag = (etag, not weak)

    # We assume the request is a new resource if it is a POST.
    new_resource = new_resource or req.method == "POST"

    # An etag will match a 'If-*-Match' header in two cases:
    #  - If it's not a new resource, and the header specifies 'anything' (i.e. '*')
    #  - Otherwise, if it's an exact match.
    def etag_matches(value):
        if value == '*' and not new_resource:
            return True
        return resp.etag == value

    if resp.is_success or resp.status_int == 304:
        if req.if_none_match is not None and etag_matches(req.if_none_match):
            if req.is_safe:
                halt(status_code=304)
            else:
                halt(status_code=412)
        elif req.if_match is not None and not etag_matches(req.if_match):
            halt(status_code=412)


def set_cache_control(resp, **kwargs):
    for key, val in kwargs.items():
        setattr(resp.cache_control, key, val)


def set_expires(resp, amount, **kwargs):
    if isinstance(amount, int):
        amount = datetime.datetime.now() + datetime.timedelta(seconds=amount)
        max_age = amount
    else:
        max_age = (datetime.datetime.now() - amount).seconds

    kwargs['max_age'] = max_age
    set_cache_control(resp, **kwargs)

    resp.expires = amount


def redirect_back(req, status_code=302):
    if req.referer is not None:
        redirect(location=req.referer, status_code=staus_code)
    else:
        return False


