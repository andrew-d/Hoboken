from __future__ import with_statement, absolute_import, print_function

import os
import re
import yaml

from hoboken.six import binary_type, text_type


def _e(val):
    if val is None:
        return None

    if isinstance(val, text_type):
        return val.encode('latin-1')
    elif isinstance(val, binary_type):
        return val
    else:
        raise ValueError("Unknown type for encoding!")  # pragma: no cover


class DeviceParser(object):
    def __init__(self, regexes):
        self.parsers = list(map(self._make_parser, regexes))

    def _make_parser(self, obj):
        replace = obj.get('device_replacement')

        regex = re.compile(_e(obj['regex']))

        return (regex, _e(replace))

    def parse(self, val):
        for regex, rep in self.parsers:
            m = regex.search(val)
            if m is not None:
                if rep is not None:
                    family = rep.replace(b'$1', m.group(1))
                else:
                    family = m.group(1)

                return family

        # If we get here, no match.
        return b'Other'


class OSClass(object):
    def __init__(self, family=None, major=None, minor=None, patch=None,
                 patch_minor=None):
        # Save attributes on self.
        self.family = family or b'Other'
        self.major = major
        self.minor = minor
        self.patch = patch
        self.patch_minor = patch_minor

    @property
    def version_string(self):
        def has_digit(b):
            return b[0:1].isdigit()

        output = []
        if self.major is not None:
            output.append(self.major)

            if self.minor is not None:
                output.append(b'.')
                output.append(self.minor)

                if self.patch is not None:
                    if has_digit(self.patch):
                        output.append(b'.')
                    output.append(self.patch)

                    if self.patch_minor is not None:
                        if has_digit(self.patch_minor):
                            output.append(b'.')

                        output.append(self.patch_minor)

        return b''.join(output)

    @property
    def full_string(self):
        suff = self.version_string
        if len(suff) > 0:
            return self.family + b' ' + suff
        else:
            return self.family


class OSParser(object):
    def __init__(self, regexes):
        self.parsers = list(map(self._make_parser, regexes))

    def _make_parser(self, obj):
        fam = obj.get('os_replacement')
        major = obj.get('os_v1_replacement')
        minor = obj.get('os_v2_replacement')
        patch = obj.get('os_v3_replacement')
        patch_minor = obj.get('os_v4_replacement')

        # Compile as a byte pattern, not text.
        regex = re.compile(_e(obj['regex']))

        return (
            regex, _e(fam), _e(major), _e(minor),
            _e(patch), _e(patch_minor)
        )

    def parse(self, val):
        for regex, family, major, minor, patch, patch_minor in self.parsers:
            m = regex.search(val)
            if m is not None:
                if family is not None:
                    if b'$1' in family:
                        family = family.replace(b'$1', m.group(1))

                    # Otherwise, family = family.
                else:
                    family = m.group(1)

                def get_match(i):
                    if m.lastindex is not None and m.lastindex >= i:
                        return m.group(i)
                    return None

                major = major or get_match(2)
                minor = minor or get_match(3)
                patch = patch or get_match(4)
                patch_minor = patch_minor or get_match(5)

                return OSClass(family, major, minor, patch, patch_minor)

        return OSClass()


class UAClass(OSClass):
    def __init__(self, family=None, major=None, minor=None, patch=None):
        self.family = family or b'Other'
        self.major = major
        self.minor = minor
        self.patch = patch
        self.patch_minor = None


class UAParser(object):
    def __init__(self, regexes):
        self.parsers = list(map(self._make_parser, regexes))

    def _make_parser(self, obj):
        fam = obj.get('family_replacement')
        major = obj.get('v1_replacement')
        minor = obj.get('v2_replacement')
        patch = obj.get('v3_replacement')

        # Compile as a byte pattern, not text.
        patt = obj['regex']
        if isinstance(patt, text_type):
            patt = patt.encode('latin-1')
        regex = re.compile(patt)

        return (regex, _e(fam), _e(major), _e(minor), _e(patch))

    def parse(self, val):
        for regex, family, major, minor, patch in self.parsers:
            m = regex.search(val)
            if m is not None:
                if family is not None:
                    if b'$1' in family:
                        family = family.replace(b'$1', m.group(1))

                    # Otherwise, family = family.
                else:
                    family = m.group(1)

                def get_match(i):
                    if m.lastindex is not None and m.lastindex >= i:
                        return m.group(i)
                    return None

                major = major or get_match(2)
                minor = minor or get_match(3)
                patch = patch or get_match(4)

                return UAClass(family, major, minor, patch)

        return UAClass()


class FullResults(OSClass):
    def __init__(self, ua, os, device):
        self.ua = ua
        self.os = os
        self.device = device

        # def parse_int(s):
        #     if s is None:
        #         return None

        #     try:
        #         return int(s)
        #     except ValueError:
        #         return 0

        self.family = ua.family
        self.major = ua.major
        self.minor = ua.minor
        self.patch = ua.patch
        self.patch_minor = None

    @property
    def full_string(self):
        s = OSClass.full_string.__get__(self)
        if self.os is not None:
            return s + b"/" + self.os.full_string
        else:
            return s


class FullParser(object):
    def __init__(self, yaml):
        self.ua_parser = UAParser(yaml['user_agent_parsers'])
        self.os_parser = OSParser(yaml['os_parsers'])
        self.device_parser = DeviceParser(yaml['device_parsers'])

    def parse_ua(self, val):
        return self.ua_parser.parse(val)

    def parse_os(self, val):
        return self.os_parser.parse(val)

    def parse_device(self, val):
        return self.device_parser.parse(val)

    def parse_all(self, val):
        ua = self.parse_ua(val)
        os = self.parse_os(val)
        device = self.parse_device(val)

        return FullResults(ua, os, device)


_yaml_path = os.path.join(os.path.dirname(__file__), "ua_regexes.yaml")
_yaml_file = open(_yaml_path, 'rb')
# _yaml_data = pkgutil.get_data('hoboken', 'objects/mixins/ua_regexes.yaml')
_yaml = yaml.load(_yaml_file)
_yaml_file.close()

# Instantiate a full parser on package import.
parser = FullParser(_yaml)


class WSGIUserAgentMixin(object):
    def __init__(self, *args, **kwargs):
        super(WSGIUserAgentMixin, self).__init__(*args, **kwargs)

    @property
    def user_agent(self):
        val = self.headers.get(b"User-Agent")
        if val is None:
            return None

        return parser.parse_all(val)

# TODO: include license from project here.
