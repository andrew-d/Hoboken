from __future__ import print_function
import re
from collections import Iterable

from hoboken.six import binary_type, text_type

def user_agent(match_re=None, **kwargs):
    # We have two cases.  If we're given a string, we assume that it is a
    # regex to match, and just handle this as-is.
    if match_re is not None:
        if isinstance(match_re, text_type):
            match_re = match_re.encode('latin-1')
        regex = re.compile(match_re)

        def user_agent_func(req):
            ua = req.headers['User-Agent']
            if regex.match(ua):
                return True
            else:
                return False

        return user_agent_func

    # Otherwise, we have a list of arguments in 'kwargs' that we match against
    # our parsed User-Agent header.

    # User-Agent conditions.
    ua_conditions = {}
    for n in ['family', 'major', 'minor', 'patch']:
        val = kwargs.pop(n, None)
        if isinstance(val, binary_type):
            val = val.decode('latin-1')
        ua_conditions[n] = val

    # OS conditions.
    os_conditions = {}
    for n in ['family', 'major', 'minor', 'patch', 'patch_minor']:
        val = kwargs.pop('os_' + n, None)
        if isinstance(val, binary_type):
            val = val.decode('latin-1')
        os_conditions[n] = val

    # Device condition.
    device = kwargs.pop('device', None)
    if isinstance(device, binary_type):
        device = device.decode('latin-1')

    # If we have more arguments, we error.
    if len(kwargs) > 0:
        msg = "Unknown condition(s) passed to user_agent(): %r" % kwargs
        logger.error(msg)
        raise TypeError(msg)

    # This is the function that does the matching.
    def user_agent_func(req):
        # Get the user-agent.
        ua = req.user_agent

        # Match
        for k, v in ua_conditions.items():
            if v is not None:
                check = getattr(ua, k, None)
                if check is not None and check != v:
                    return False

        for k, v in os_conditions.items():
            if v is not None:
                check = getattr(ua.os, k, None)
                if check is not None and check != v:
                    return False

        if device is not None and device != ua.device:
            return False

        return True

    return user_agent_func


def host(match_re):
    if isinstance(match_re, text_type):
        match_re = match_re.encode('latin-1')
    regex = re.compile(match_re)

    def host_func(req):
        return regex.match(req.host)

    return host_func


def accepts(mimetypes):
    # Note that we can't simply check for an iterable here, since
    # strings are also iterables.
    if isinstance(mimetypes, list):
        will_accept_raw = mimetypes
    else:
        will_accept_raw = [mimetypes]

    # Encode the list.
    will_accept = []
    for x in will_accept_raw:
        if isinstance(x, text_type):
            will_accept.append(x.encode('latin-1'))
        else:
            will_accept.append(x)

    def accepts_func(req):
        for a in will_accept:
            if a in req.accept_mimetypes:
                return True

        return False

    return accepts_func

