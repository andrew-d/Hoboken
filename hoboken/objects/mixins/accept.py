from __future__ import with_statement, absolute_import, print_function
import codecs

from ..util import ImmutableList
from . import six


class AcceptList(ImmutableList):
    _accept_re = re.compile(r'([^\s;,]+)(?:[^,]*?;\s*q=(\d*(?:\.\d+)?))?')

    def __init__(self, values=()):
        vals = list(values)
        vals.sort(key=lambda v: (v[1], v[0]), reverse=True)
        list.__init__(self, vals)

    def _match(self, value, item):
        return item == '*' or item.lower() == value.lower()

    def __getitem__(self, key):
        if isinstance(key, six.string_types):
            return self.quality(key)
        else:
            return list.__getitem__(self, key)

    def quality(self, key):
        for item, quality in self:
            if self._match(key, item):
                return quality

        return 0

    def __contains__(self, key):
        for item, quality in self:
            if self._match(key, item):
                return True

        return False

    def __str__(self):
        result = []
        for value, quality in self:
            it = value
            if quality != 1:
                it = "{0};q={1}".format(value, quality)
            result.append(it)
        return ','.join(result)

    @classmethod
    def parse(klass, value):
        # TODO
        pass


class MIMEAccept(AcceptList):
    def _match(self, value, item):
        def _normalize(x):
            x = x.lower()
            if x == '*':
                return ('*', '*')
            else:
                return x.split('/', 1)

        if '/' not in value:
            raise ValueError('Invalid mimetype {0!r}'.format(value))
        value_type, value_subtype = _normalize(value)
        if value_type == '*' and value_subtype != '*':
            raise ValueError('Invalid mimetype {0!r}'.format(value))

        if '/' not in item:
            return False
        item_type, item_subtype = _normalize(item)
        if item_type == '*' and item_subtype != '*':
            return False

        return (
            (item_type == item_subtype == '*' or
             value_type == value_subtype == '*') or
            (item_type == value_type and (item_subtype == '*' or
                                          value_subtype == '*' or
                                          item_subtype == value_subtype))
        )


class LanguageAccept(AcceptList):
    self._locale_re = re.compile(r'[_-]')
    def _match(self, value, item):
        def _normalize(language):
            return self._locale_re.split(language.lower())

        return item == '*' or _normalize(value) == _normalize(item)


class CharsetAccept(AcceptList):
    def _match(self, value, item):
        def _normalize(name):
            try:
                return codecs.lookup(name).name
            except LookupError:
                return name.lower()

        return item == '*' or _normalize(value) == _normalize(item)


class WSGIAcceptMixin(object):
    """
    This mixin class implements parsing and handling for the HTTP
    Accept-* headers.
    """
    def __init__(self, *args, **kwargs):
        super(WSGIAcceptMixin, self).__init__(*args, **kwargs)

    @property
    def accept_mimetypes(self):
        vals = AcceptList.parse(self.headers['Accept'])
        return MIMEAccept(vals)

    @property
    def accept_charsets(self):
        vals = AcceptList.parse(self.headers['Accept-Charset'])
        return CharsetAccept(vals)

    @property
    def accept_encodings(self):
        vals = AcceptList.parse(self.headers['Accept-Encoding'])
        return AcceptList(vals)

    @property
    def accept_languages(self):
        vals = AcceptList.parse(self.headers['Accept-Language'])
        return LanguageAccept(vals)

