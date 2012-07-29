from __future__ import print_function
import re
from collections import Iterable
from webob.acceptparse import MIMEAccept

def user_agent(match_re):
    regex = re.compile(match_re)

    def user_agent_func(req):
        ua = req.headers['User-Agent']
        if regex.match(ua):
            return True
        else:
            return False

    return user_agent_func


def host(match_re):
    regex = re.compile(match_re)

    def host_func(req):
        return regex.match(req.host)

    return host_func


def accepts(mimetypes):
    # Note that we can't simply check for an iterable here, since
    # strings are also iterables.
    if isinstance(mimetypes, list):
        will_accept = mimetypes
    else:
        will_accept = [mimetypes]

    def accepts_func(req):
        for a in will_accept:
            # print('matching {0} against {1}'.format(str(req.accept), str(a)))
            #if str(req.accept) in a:
            if a in req.accept:
                return True

        return False

    return accepts_func

