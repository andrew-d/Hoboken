from __future__ import with_statement, absolute_import, print_function

from . import six

class WSGICacheMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIAcceptMixin, self).__init__(*args, **kwargs)

    # TODO:
    #   - Need to handle request vs. response directives
    #   - Accessors like, e.g.: response.max_age = 1234, or request.no_cache = True
    #   - The 'Age' HTTP header
    #   - The 'Expires' HTTP header
    #   - 'Pragma: no-cache' --> 'Cache-Control: no-cache'
    #   - The 'Vary' HTTP header
    #   - 

