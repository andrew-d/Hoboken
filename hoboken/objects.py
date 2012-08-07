# Future-proofing
from __future__ import with_statement, absolute_import, print_function

import webob

class Request(webob.BaseRequest):
    """
    Hoboken's request objects.  Uses WebOb's request object
    """
    @property
    def is_safe(self):
        """
        Returns True if the request is considered "safe" - i.e. if the request
        should be treated as not modifying any state.
        """
        return self.method in ['GET', 'HEAD', 'OPTIONS', 'TRACE']

    @property
    def is_idempotent(self):
        """
        Returns True if the request is considered idempotent - i.e. if two
        successive identical requests should result in the same result.
        """
        return self.is_safe or self.method in ['PUT', 'DELETE']


class Response(webob.Response):
    """
    Hoboken's request objects.  Uses WebOb's request object.
    """
    @property
    def is_informational(self):
        return 100 <= self.status_int <= 199

    @property
    def is_success(self):
        return 200 <= self.status_int <= 299

    @property
    def is_redirect(self):
        return 300 <= self.status_int <= 399

    @property
    def is_client_error(self):
        return 400 <= self.status_int <= 499

    @property
    def is_server_error(self):
        return 500 <= self.status_int <= 599

    @property
    def is_not_found(self):
        return self.status_int == 404


