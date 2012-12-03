from __future__ import with_statement, absolute_import, print_function

from hoboken.six import binary_type, iteritems, reraise, text_type

# NOTE: much of the following code is taken from WebOb - an inspiration for
# this functionality.  Thanks, guys!


class WSGIRequestBuilderMixin(object):
    """
    This mixins allows one to build a request by calling the build classmethod.
    """
    # Set our response class to None by default - it gets filled in later
    # to avoid circular imports.
    ResponseClass = None

    def __init__(self, *args, **kwargs):
        super(WSGIRequestBuilderMixin, self).__init__(*args, **kwargs)

    @classmethod
    def build(klass, path, charset='utf-8', **kwargs):
        """
        This function lets us build a request by creating a base, empty WSGI
        environ, and then filling it in with the appropriate values.
        """
        # Encode our path as bytes if necessary.
        if isinstance(path, text_type):
            path = path.encode(charset)

        # Build a temporary environ.
        env = {
            'SERVER_PROTOCOL': 'HTTP/1.0',
            'SCRIPT_NAME': '',
            'PATH_INFO': path,

            # WSGI variables.
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }

        def try_add(arg, key, default=None):
            val = kwargs.get(arg, default)
            if val is not None:
                env[key] = val

        try_add('query_string', 'QUERY_STRING')
        try_add('method', 'REQUEST_METHOD', 'GET')
        try_add('server_name', 'SERVER_NAME', 'localhost')
        try_add('server_port', 'SERVER_PORT', '80')

        # Create our request.
        req = klass(env)

        # Set headers.
        headers = kwargs.get('headers')
        if headers is not None:
            for header, value in iteritems(headers):
                req.headers[header] = value

        # Done!
        return req

    def call_application(self, wsgi_app, catch_exc_info=False):
        """
        This function will call a given WSGI application with the current
        request, and then return the response as a Response objects.
        """
        # Create lists to store our return values and output.
        captured = []
        output = []

        # This function gets passed to the application.
        def start_response(status, headers, exc_info=None):
            if exc_info is not None and not catch_exc_info:
                reraise(exc_info)
            captured[:] = [status, headers, exc_info]

            # The write() callable should append to our output list.
            return output.append

        # Actually call the application.
        app_iter = wsgi_app(self.environ, start_response)

        # If we have output, or no return value, we try and read our return
        # iterator.
        if output or not captured:
            try:
                output.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()
            app_iter = output

        # Return the appropriate information.
        if catch_exc_info:
            return (captured[0], captured[1], app_iter, captured[2])
        else:
            return (captured[0], captured[1], app_iter)

    def get_response(self, wsgi_app, catch_exc_info=False):
        """
        This function will use the above call_application to call an app, and
        then return a response object.
        """
        # Ignore exception info here.
        if catch_exc_info:
            status, headers, app_iter, exc_info = self.call_application(
                wsgi_app, catch_exc_info=True)
            del exc_info
        else:
            status, headers, app_iter = self.call_application(
                wsgi_app, catch_exc_info=False)

        # Set values on response and return.
        resp = self.ResponseClass()
        resp.status = status
        resp.headers = list(headers)
        resp.response_iter = app_iter
        return resp

