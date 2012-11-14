from __future__ import with_statement, absolute_import, print_function

import re
from hoboken.six import binary_type
from hoboken.objects.oproperty import property_overriding, oproperty


ETAG_RE = re.compile(br'(?:^|\s)(W/)?"((?:\\"|.)*?)"')


class _MatchAnyEtag(object):
    """
    This class represents an ETag that matches anything.
    """
    def __repr__(self):
        return "<MatchAnyEtag>"

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__

    def __contains__(self, other):
        return True

    def __str__(self):
        return "*"


class _MatchNoneEtag(object):
    """
    This class represents an ETag that matches nothing.
    """
    def __repr__(self):
        return "<MatchNoneEtag>"

    def __nonzero__(self):
        return False

    __bool__ = __nonzero__

    def __contains__(self, other):
        return False

    def __str__(self):
        return ""


# Initialized objects of our ETag classes.
MatchAnyEtag = _MatchAnyEtag()
MatchNoneEtag = _MatchNoneEtag()


class WSGIRequestEtagMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIRequestEtagMixin, self).__init__(*args, **kwargs)

    def _parse_etag_value(self, value, strong_only):
        # If this value is "*", we return the Match Any etag.
        if value == b'*':
            return MatchAnyEtag

        # Find all Etags in the header.
        matches = ETAG_RE.findall(value)
        if matches:
            if strong_only:
                return tuple(
                    tag.replace(b'\\"', b'"') for weak, tag in matches \
                    if not weak
                )
            else:
                return tuple(tag.replace(b'\\"', b'"') for weak, tag in matches)

        # No matches.  We just return the value, unmodified.
        return (value,)

    @property
    def if_match(self):
        val = self.headers.get('If-Match')
        if val is None:
            return MatchAnyEtag
        else:
            # NOTE: According to section 14.24 of the HTTP spec:
            #   "A server MUST use the strong comparison function (see section
            #   13.3.3) to compare the entity tags in If-Match."
            return self._parse_etag_value(val, True)

    @property
    def if_none_match(self):
        val = self.headers.get('If-None-Match')
        if val is None:
            return MatchNoneEtag
        else:
            # Section 14.26 of the HTTP spec:
            #   "The weak comparison function can only be used with GET or HEAD
            #   requests."
            if self.method in ['GET', 'HEAD']:
                return self._parse_etag_value(val, False)
            else:
                return self._parse_etag_value(val, True)


class WSGIResponseEtagMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIResponseEtagMixin, self).__init__(*args, **kwargs)

    @property
    def etag(self):
        etag = self.headers.get('Etag')
        if etag is None:
            return None

        # Parse the etag value.
        matches = ETAG_RE.match(etag)

        # If we don't get a value, we return it anyway.
        if matches is None:
            return etag

        # Return a tuple in the form (etag, is_strong)
        is_strong = not bool(matches.group(1))
        etag = matches.group(2).replace('\\"', '"')
        return (etag, is_strong)

    @etag.setter
    def etag(self, val):
        if isinstance(val, tuple):
            # The (etag, is_strong) case.
            val, strong = val
        elif isinstance(val, binary_type):
            # Just setting an etag.
            strong = True
        else:
            raise ValueError("You can only set an ETag to a binary value, or a"
                             "tuple in the form (etag, bool)")

        if ETAG_RE.match(val):
            # Already a valid Etag - do nothing.
            new_val = val
        else:
            # Quote the ETag.
            if strong:
                new_val = '"%s"' % (val.replace('"', '\\"'),)
            else:
                new_val = 'W/"%s"' % (val.replace('"', '\\"'),)

        self.headers['Etag'] = new_val

