from __future__ import with_statement, absolute_import, print_function

from abc import ABCMeta, abstractproperty
from hoboken.six import with_metaclass


class BaseRequest(with_metaclass(ABCMeta)):
    """
    Hoboken's request object.  This class defines the interface that all
    request objects must follow.
    """
    @abstractproperty
    def http_version(self):
        raise NotImplementedError()

    @abstractproperty
    def url(self):
        raise NotImplementedError()
    @abstractproperty
    def path(self):
        raise NotImplementedError()

    # TODO: do we want these in all cases? i.e. if we're not a WSGI
    # application, do we care about these? possibly rename these to the names
    # below:
    # mount_point: where the script is mounted - i.e. "/" in the script is what
    #              path for the user?
    # script_path: the part of the path that the current application cares
    #              about
    @abstractproperty
    def script_name(self):
        raise NotImplementedError()
    @abstractproperty
    def path_info(self):
        raise NotImplementedError()


    @abstractproperty
    def host(self):
        raise NotImplementedError()
    @abstractproperty
    def port(self):
        raise NotImplementedError()

    @abstractproperty
    def scheme(self):
        raise NotImplementedError()

    @abstractproperty
    def method(self):
        raise NotImplementedError()

    @abstractproperty
    def query_string(self):
        raise NotImplementedError()

    @abstractproperty
    def input_stream(self):
        raise NotImplementedError()


    # TODO: do these belong here?
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

    @property
    def is_secure(self):
        """Returns true if the request is made using HTTPS."""
        return self.scheme == b'https'



class BaseResponse(with_metaclass(ABCMeta)):
    """
    Hoboken's response object.
    """
    @abstractproperty
    def status_int(self):
        raise NotImplementedError()

    @abstractproperty
    def status_text(self):
        raise NotImplementedError()

    @abstractproperty
    def status(self):
        raise NotImplementedError()

    @abstractproperty
    def headers(self):
        raise NotImplementedError()

    # Response body
    # -------------------------------------------

    @abstractproperty
    def response_iter(self):
        """
        The base iterator for a response.
        """
        raise NotImplementedError()

    # TODO: do these belong here?
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


