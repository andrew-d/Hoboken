from __future__ import with_statement, absolute_import, print_function

from . import six

class WSGICacheMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIAcceptMixin, self).__init__(*args, **kwargs)

