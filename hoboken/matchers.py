# Future-proofing
from __future__ import with_statement, absolute_import

# Stdlib dependencies
import re

# In-package dependencies
from .exceptions import *
from .compat import *


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
            matches = self.path == webr.path
        else:
            matches = self.path.lower() == webr.path.lower()

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
        elif isinstance(regex, BaseStringType):
            try:
                self.re = re.compile(regex)
            except re.error:
                raise TypeError("Parameter 'regex' is not a valid regex")
        else:
            raise TypeError("Parameter 'regex' is not a valid regex")

        # Save keys.
        self.key_types = key_types
        self.key_names = key_names

    def match(self, webr):
        match = self.re.match(webr.path)
        if match:
            matches = match.groups()

            # Merge in the captures.
            for t, k, v in zip(self.key_types, self.key_names, matches):
                # Depending on the type, either add to urlargs or urlparams.
                if t == True:
                    if k is not None:
                        webr.urlvars[k] = v
                else:
                    webr.urlargs = webr.urlargs + (v,)

            # We save all captures in the special parameter "_captures".
            webr.urlvars["_captures"] = list(matches)

            # Success!
            return True
        else:
            return False

    def reverse(self, args, kwargs):
        # We cannot reverse a regex.
        return False

    def __str__(self):
        return self.re.pattern

    def __repr__(self):
        return "RegexMatcher(regex={0!r}, key_types={1!r}, key_names={2!r})".format(self.re.pattern, self.key_types, self.key_names)


class HobokenRouteMatcher(AbstractMatcher):
    ENCODING_REGEX = re.compile(r"[^?%\\/:*\w]")
    MATCH_REGEX = re.compile(r"((:\w+)|\*)")

    def __init__(self, route):
        match_regex = self._convert_path(route)
        self.match_re = re.compile(match_regex)

    def _encode_character(self, char):
        """
        This function will encode a given character as a regex that will match
        it in either regular or encoded form.
        """
        encode_char = lambda c: re.escape("%" + hex(ord(c))[2:])

        # Was trying to use urllib.quote here, but it tries to encode too much for
        # my liking.  Just using a regex.
        if re.match(r"[;/?:@&=,\[\]]", char):
            encoded = encode_char(char)
        else:
            encoded = char

        # If the encoded version is unchanged, then we match both
        # the bare version, along with the encoded version.
        if encoded == char:
            encoded = "(?:" + re.escape(char) + "|" + encode_char(char) + ")"

        # Specifically for the space charcter, we match everything, and also plus characters.
        if char == ' ':
            encoded = "(?:" + encoded + "|" + self._encode_character("+") + ")"

        return encoded

    def _convert_path(self, match):
        """
        This function will convert a Hoboken-style route path into a regex, and
        also save enough information that we can reverse this path, given some
        args and kwargs.
        """

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

        # The 'keys' array will store the name of the current segment - i.e.
        # 'param' if the segment is ':param', or None if it's a splat.
        # The types array will store False if the current segment is a splat,
        # and True if it's a parameter.  We use these arrays when matching to
        # determine whether to return a match as an arg or kwarg.
        self.group_names = {}

        # Store the fragments between matches, so that we can rebuild the path,
        # given a route.
        self.fragments = []
        last_fragment = 0
        for m in self.MATCH_REGEX.finditer(match):
            frag_start = last_fragment
            frag_end = m.start(0)
            frag_content = match[frag_start:frag_end]
            # print("Fragment: {0} --> {1} ({2})".format(frag_start, frag_end, frag_content))
            self.fragments.append(frag_content)

            last_fragment = m.end(0)

        # This class gets around the lack of the nonlocal keyword on python 2.X
        class Store(object):
            num_groups = 0

        def convert_match(match):
            # Store the fragment.
            group_num = Store.num_groups
            Store.num_groups += 1

            # print("Group {0} starts at position {1}, is '{2}'".format(group_num, match.start(0), match.group(0)))

            # Return the appropriate regex.
            if match.group(0) == '*':
                self.group_names[group_num] = None
                return r"(.*?)"
            else:
                self.group_names[group_num] = match.group(0)[1:]
                return r"([^/?#]+)"

        # Wrapper function that simply passes through to encode_character() with
        # the match's content.
        def encode_character_wrapper(match):
            return self._encode_character(match.group(0))

        # Encode everything that's not in the set:
        #   [?%\/:*] + all alphanumeric characters + underscore.
        encoded_match = self.ENCODING_REGEX.sub(encode_character_wrapper, match)

        # Now, replace parameters or splats with their matching regex.
        match_regex = self.MATCH_REGEX.sub(convert_match, encoded_match)

        # We need to add the begin/end anchors, because otherwise the lazy
        # matches in our splats won't match anything.
        match_regex = "^" + match_regex + "$"
        return match_regex

    def match(self, request):
        match = self.match_re.match(request.path)
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
        for i in range(num_fragments):
            final_route += self.fragments[i]

            group_name = self.group_names[i]
            if group_name is None:
                final_route += args[args_index]
                args_index += 1
            else:
                final_route += kwargs[group_name]

        return final_route

