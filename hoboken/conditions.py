from __future__ import print_function
import re
from collections import Iterable

from hoboken.six import text_type

def user_agent(match_re):
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
            # print('matching {0} against {1}'.format(str(req.accept), str(a)))
            #if str(req.accept) in a:
            if a in req.accept_mimetypes:
                return True

        return False

    return accepts_func

