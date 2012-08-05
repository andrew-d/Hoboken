from __future__ import with_statement, absolute_import, print_function

from .application import halt
import time
import datetime
import webob


class HobokenCachingMixin(object):
    """
    This class defines a mixin that one can combine with the base
    HobokenApplication to add some handy helpers for dealing with caching.
    """
    def __init__(self):
        raise NotImplementedError("Hoboken mixins cannot be instantiated!")

    def check_last_modified(self, date):
        """
        This function will check if one of a given request's last modified headers
        are set, and, if so, will check it against the date provided.  If the
        request specifies an equivalent or newer resource, this function will call
        halt() to abort the current request with a 304 Not Modified status.
        """
        if date is None:
            return

        # Python's time functions are stupid.  We do everything with unix times.
        timestamp = time.mktime(date.timetuple())
        self.response.last_modified = timestamp

        # We don't do anything if there's an ETag.
        if self.request.if_none_match is not webob.etag.NoETag:
            return

        print("Status:", self.response.status_int, "If-Modified-Since:", self.request.if_modified_since)

        if self.response.status_int == 200 and self.request.if_modified_since is not None:
            time_val = time.mktime(self.request.if_modified_since.timetuple())
            print("If-Modified-Since:", time_val, "Date:", timestamp)
            if time_val >= timestamp:
                halt(status_code=304)

        if ((self.response.is_success or self.response.status_int == 412) and
             self.request.if_unmodified_since is not None):
            time_val = time.mktime(self.request.if_unmodified_since.timetuple())
            print("If-Unmodified-Since:", time_val, "Date:", timestamp)
            if time_val < timestamp:
                halt(status_code=412)

    def check_etag(self, etag, new_resource=None, weak=False):
        """
        As per check_if_modified(), except checks the ETag header instead.
        """
        self.response.etag = (etag, not weak)

        # We assume the request is a new resource if it is a POST.
        new_resource = new_resource or self.request.method == "POST"

        # An etag will match a 'If-*-Match' header in two cases:
        #  - If it's not a new resource, and the header specifies 'anything' (i.e. '*')
        #  - Otherwise, if it's an exact match.
        def etag_matches(value):
            if value == '*' and not new_resource:
                return True
            return self.response.etag in value

        if self.response.is_success or self.response.status_int == 304:
            if self.request.if_none_match is not None and etag_matches(self.request.if_none_match):
                if self.request.is_safe:
                    halt(status_code=304)
                else:
                    halt(status_code=412)
            elif self.request.if_match is not None and not etag_matches(self.request.if_match):
                halt(status_code=412)

    def set_cache_control(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self.response.cache_control, key, val)

    def set_expires(self, amount, **kwargs):
        if isinstance(amount, int):
            amount = datetime.datetime.now() + datetime.timedelta(seconds=amount)
            max_age = amount
        else:
            max_age = (datetime.datetime.now() - amount).seconds

        kwargs['max_age'] = max_age
        self.set_cache_control(**kwargs)

        self.response.expires = amount


class HobokenRedirectMixin(object):
    def __init__(self):
        raise NotImplementedError("Hoboken mixins cannot be instantiated!")

    def redirect_back(self, *args, **kwargs):
        """
        This is a helper function to redirect 'back' - i.e. to whichever page
        referred to this one.
        TODO: emit HTML to redirect back if no referrer.
        """
        if self.request.referer is not None:
            self.redirect(location=self.request.referer, *args, **kwargs)
        # TODO: do we want to do this?
        # elif 'text/html' in self.request.accept:
        #     body_text = """
        #     <html><body onload="history.go(-1);">Please go back one page</body></html>
        #     """

        #     halt(status_code=200, text=body_text)
        else:
            return False

    def redirect_to(self, func, status_code=None, *args, **kwargs):
        """
        This is a helper function to redirect to another route.
        """
        location = self.url_for(func, *args, **kwargs)
        self.redirect(location, status_code=status_code)



