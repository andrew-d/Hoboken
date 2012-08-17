# Future-proofing
from __future__ import with_statement, absolute_import

# Stdlib dependencies
import re
import sys

# In-package dependencies
from .exceptions import *

# Compatibility.
from .six import string_types, text_type, PY3

RegexType = type(re.compile(""))
RegexMatchType = type(re.compile(".*").match("asdf"))


class AbstractMatcher(object):
    """
    This class is the abstract class for all matchers that are used by Hoboken.
    """
    def match(self, request):
        """
        This function performs matching against a given Request.  If the
        request matches, then this function will return (True, args, kwargs),
        where args and kwargs are optional parameters to be passed to the route
        function.  If the request does not match, then this function must
        return (False, _, _), where the underscores are any value.
        """
        raise NotImplementedError("match() is not implemented in the base class")

    def reverse(self, args, kwargs):
        """
        This function provides support for reversing - i.e. given arguments,
        return the associate path.  This function must either return a string
        representing the reversed path, or None if the route cannot be reversed
        (either because there's no support for reversal, or because the passed
        parameters were invalid).
        """
        raise NotImplementedError("reverse() is not implemented in the base class")


class BasicMatcher(AbstractMatcher):
    """
    Basic matcher - just checks if the path matches exactly.
    """
    def __init__(self, path, case_sensitive=True):
        self.path = path
        self.case_sensitive = case_sensitive

    def match(self, request):
        if self.case_sensitive:
            matches = self.path == request.path_info
        else:
            matches = self.path.lower() == request.path_info.lower()

        # No arguments, so always return empty values.
        return matches, [], {}

    def reverse(self, args, kwargs):
        # Reversing a basic route is just the path itself.
        return self.path

    def __str__(self):
        return self.path

    def __repr__(self):
        return "BasicMatcher(path={0!s}, case_sensitive={1}".format(self.path, self.case_sensitive)


class RegexMatcher(AbstractMatcher):
    """
    This class matches a URL using a provided regex.
    """

    def __init__(self, regex, key_types, key_names):
        # We handle regexes and string patterns for regexes here.
        if isinstance(regex, RegexType):
            self.re = regex
        elif isinstance(regex, string_types):     # pragma: no cover
            try:
                self.re = re.compile(regex)
            except re.error:
                raise TypeError("Parameter 'regex' is not a valid regex")
        else:                                       # pragma: no cover
            raise TypeError("Parameter 'regex' is not a valid regex")

        # Save keys.
        self.key_types = key_types
        self.key_names = key_names

    def match(self, request):
        match = self.re.match(request.path_info)
        args = []
        kwargs = {}

        if match:
            matches = match.groups()

            # Merge in the captures.
            for t, k, v in zip(self.key_types, self.key_names, matches):
                # Depending on the type, either add to urlargs or urlparams.
                if t == True:
                    if k is not None:
                        kwargs[k] = v
                else:
                    args.append(v)

            # We save all captures in the special parameter "_captures".
            kwargs["_captures"] = list(matches)

        return match, args, kwargs

    def reverse(self, args, kwargs):
        # We cannot reverse a regex.
        return False

    def __str__(self):
        return self.re.pattern

    def __repr__(self):
        return "RegexMatcher(regex={0!r}, key_types={1!r}, key_names={2!r})".format(self.re.pattern, self.key_types, self.key_names)


class HobokenRouteMatcher(AbstractMatcher):
    # These regexes mirror those of Ruby's URI module.
    ALPHANUMERIC = b"A-Za-z0-9"
    UNRESERVED = br"\-_.!~*'()" + ALPHANUMERIC
    RESERVED = Br";/?:@&=+$,\[\]"
    UNSAFE = br"[^" + UNRESERVED + RESERVED + b"]"
    unsafe_re = re.compile(UNSAFE)

    # This regex is what we use to find params/splats.
    MATCH_REGEX_PATTERN = r'((:\w+)|\*)'
    MATCH_REGEX_BYTES = re.compile(MATCH_REGEX_PATTERN.encode('latin-1'))
    MATCH_REGEX_STR = re.compile(MATCH_REGEX_PATTERN)

    def __init__(self, route):
        match_regex = self._convert_path(route)
        self.match_re = re.compile(match_regex)

    def _save_fragments(self, match):
        """
        Store the fragments between matches, so that we can rebuild the path,
        given a route.
        """
        self.fragments = []
        last_fragment = 0
        for m in self.MATCH_REGEX_STR.finditer(match):
            frag_start = last_fragment
            frag_end = m.start(0)
            frag_content = match[frag_start:frag_end]
            self.fragments.append(frag_content)

            last_fragment = m.end(0)

        # Add the final fragment (or a blank string).
        if last_fragment != len(match):
            self.fragments.append(match[last_fragment:])
        else:
            self.fragments.append('')

    def _url_encode_char(self, c):
        c = hex(ord(c))[2:].upper()
        c = b'%' + c.encode('ascii').zfill(2)
        return c

    def _url_encode(self, c):
        if self.unsafe_re.match(c) is not None:
            c = self._url_encode_char(c)
        return c

    def _convert_path(self, path):
        """
        This function will convert a Hoboken-style route path into a regex, and
        also save enough information that we can reverse this path, given some
        args and kwargs.
        """

        # Before we do anything else, save the fragments of the path so we can
        # reconstruct it.
        self._save_fragments(path)

        # We need to extract the splats, the named parameters, and then create
        # a regex to match it.
        #
        # The general rules are as follows:
        #  - Block parameters like :block match one path segment -
        #    i.e. until the next "/", special character, or end-of-
        #    string.  Note that blocks must match at least one
        #    character.
        #  - Splats match anything, but always match non-greedily.
        #    Splats can also match the empty string (i.e. nothing).
        #
        # So, we convert to a regex in the following way:
        #  - Blocks are converted like this:
        #      blah:block --> r"blah([^/?#]+)"
        #  - Splats are converted like this:
        #      blah*blah  --> r"blah(.*?)blah"

        # This class gets around the lack of the nonlocal keyword on python 2.X
        class Store(object):
            ignore = b""
            num_groups = 0

        # This function escapes a character with regex encoding and url-encoding.
        def escaped(c):
            return [re.escape(x) for x in [c, self._url_encode_char(c)]]

        # This function will return a regex that matches a given character in
        # any of the ways it might appear in a URL.  Note that we special-case
        # spaces to also match plus signs.
        def encoded(c):
            # We handle the case of Space specifically.
            if c == b' ':
                return b'(?:\%20' + b'|' + encoded(b'+') + b')'

            # If the encoding doesn't change, we match both the encoded and un-
            # encoded version.  Otherwise, we match just the encoded version.
            # Note that we regex-escape in all cases.
            char = self._url_encode(c)
            if char == c:
                char = b'(?:' + b'|'.join(escaped(c)) + b')'
            else:
                char = re.escape(char)

            return char

        # This function will convert a matched character into the proper encoding.
        def encode_character(match):
            char = match.group(0)
            if char == b'.' or char == b'@':
                Store.ignore += b''.join(escaped(char))
            return encoded(char)

        # This dict stores group names - 'None' for a splat, otherwise the name
        # of the param.
        self.group_names = {}

        def convert_match(match):
            # Get the group number.
            group_num = Store.num_groups
            Store.num_groups += 1

            # Return the appropriate regex.
            if match.group(0) == b'*':
                self.group_names[group_num] = None
                return br"(.*?)"
            else:
                self.group_names[group_num] = match.group(0)[1:].decode('ascii')
                return br"([^" + Store.ignore + br"/?#]+)"

        # Before we do anything else, we ensure that the input route is a byte
        # type.  If it's a text type, we encode it as UTF-8.
        if isinstance(path, text_type):
            path = path.encode('utf-8')

        pattern = re.sub(br'[^\?\%\\\/\:\*\w]', encode_character, path)
        pattern = self.MATCH_REGEX_BYTES.sub(convert_match, pattern)
        pattern = br'\A' + pattern + br'\Z'

        return pattern.decode('ascii')

    def match(self, request):
        match = self.match_re.match(request.path_info)
        args = []
        kwargs = {}

        does_match = (match is not None)
        if does_match:
            groups = list(match.groups())
            for idx in range(len(groups)):
                group_name = self.group_names[idx]
                if group_name is None:
                    args.append(groups[idx])
                else:
                    kwargs[group_name] = groups[idx]

        return does_match, args, kwargs

    def reverse(self, args, kwargs):
        num_fragments = len(self.fragments)
        final_route = ""
        args_index = 0

        # For each fragment, we append it, and then lookup the associated type
        # for the current group.  If it's an arg, we grab the current arg and
        # then increment the arg count, otherwise we grab the right kwarg.
        for i in range(num_fragments - 1):
            final_route += self.fragments[i]

            group_name = self.group_names[i]
            if group_name is None:
                final_route += args[args_index]
                args_index += 1
            else:
                value = kwargs[group_name] or ''
                final_route += value

        return final_route + self.fragments[-1]

