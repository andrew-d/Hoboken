from __future__ import with_statement, absolute_import, print_function
import re
import codecs

from ..util import ImmutableList
from . import six

class AcceptList(ImmutableList):
    _accept_re = re.compile(br'([^\s;,]+)(?:[^,]*?;\s*q=(\d*(?:\.\d+)?))?')

    def __init__(self, values=None):
        vals = list(values or ())
        vals.sort(key=lambda v: (v[1], v[0]), reverse=True)
        list.__init__(self, vals)

    def _match(self, value, item):
        return item == b'*' or item.lower() == value.lower()

    def __getitem__(self, key):
        if isinstance(key, six.text_type):
            return self.quality(key.encode('utf-8'))
        elif isinstance(key, six.binary_type):
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

    def to_bytes(self):
        result = []
        for value, quality in self:
            it = value
            if quality != 1:
                q = str(quality)
                if six.PY3:
                    q = q.encode('latin-1')
                it = value + b';q=' + q
            result.append(it)
        return b', '.join(result)

    @classmethod
    def parse(klass, value):
        if not value:
            return None

        ret = []
        for match in klass._accept_re.finditer(value):
            quality = match.group(2)
            if not quality:
                quality = 1.0
            else:
                quality = min(max(float(quality), 0.0), 1.0)
            ret.append((match.group(1), quality))

        return klass(ret)


class MIMEAccept(AcceptList):
    def _match(self, value, item):
        def _normalize(x):
            x = x.lower()
            if x == b'*':
                return (b'*', b'*')
            else:
                return x.split(b'/', 1)

        if b'/' not in value:
            raise ValueError('Invalid mimetype {0!r}'.format(value))
        value_type, value_subtype = _normalize(value)
        if value_type == b'*' and value_subtype != b'*':
            raise ValueError('Invalid mimetype {0!r}'.format(value))

        if b'/' not in item:
            return False
        item_type, item_subtype = _normalize(item)
        if item_type == b'*' and item_subtype != b'*':
            return False

        return (
            (item_type == item_subtype == b'*' or
             value_type == value_subtype == b'*') or
            (item_type == value_type and (item_subtype == b'*' or
                                          value_subtype == b'*' or
                                          item_subtype == value_subtype))
        )


class LanguageAccept(AcceptList):
    _locale_re = re.compile(br'[_-]')
    def _match(self, value, item):
        def _normalize(language):
            return self._locale_re.split(language.lower())

        return item == b'*' or _normalize(value) == _normalize(item)


class CharsetAccept(AcceptList):
    def _match(self, value, item):
        def _normalize(name):
            try:
                if six.PY3 and isinstance(name, bytes):
                    name = name.decode('utf-8')
                return codecs.lookup(name).name
            except LookupError:
                return name.lower()

        return item == b'*' or _normalize(value) == _normalize(item)


class WSGIAcceptMixin(object):
    """
    This mixin class implements parsing and handling for the HTTP
    Accept-* headers.
    """
    def __init__(self, *args, **kwargs):
        super(WSGIAcceptMixin, self).__init__(*args, **kwargs)

    @property
    def accept_mimetypes(self):
        vals = AcceptList.parse(self.headers.get('Accept'))
        return MIMEAccept(vals)

    @property
    def accept_charsets(self):
        vals = AcceptList.parse(self.headers.get('Accept-Charset'))
        return CharsetAccept(vals)

    @property
    def accept_encodings(self):
        vals = AcceptList.parse(self.headers.get('Accept-Encoding'))
        return AcceptList(vals)

    @property
    def accept_languages(self):
        vals = AcceptList.parse(self.headers.get('Accept-Language'))
        return LanguageAccept(vals)

    # Helper functions that test common accept values.
    @property
    def accepts_json(self):
        return b'application/json' in self.accept_mimetypes

    @property
    def accepts_xhtml(self):
        return (
            b'application/xhtml+xml' in self.accept_mimetypes or
            b'application/xml' in self.accept_mimetypes
        )

    @property
    def accepts_html(self):
        return (
            b'text/html' in self.accept_mimetypes or
            self.accepts_xhtml
        )

