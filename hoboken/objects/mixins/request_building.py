from __future__ import with_statement, absolute_import, print_function

from hoboken.six import binary_type, iteritems, text_type

class WSGIRequestBuilderMixin(object):
    """
    This mixins allows one to build a request by calling the build classmethod.
    """
    def __init__(self, *args, **kwargs):
        super(WSGIRequestBuilderMixin, self).__init__(*args, **kwargs)

    @classmethod
    def build(klass, path, charset='utf-8', **kwargs):
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
                self.headers[header] = value

        # Done!
        return req

    def get_response(self, wsgi_app):
        pass

