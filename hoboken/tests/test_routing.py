from . import HobokenTestCase, hoboken
import os
import yaml
import unittest

import pytest

from hoboken.application import Request
from hoboken.six import iteritems, text_type
Matcher = hoboken.matchers.HobokenRouteMatcher


class TestMethods(HobokenTestCase):
    def after_setup(self):
        for meth in self.app.SUPPORTED_METHODS:
            self.app.add_route(meth, '/', self.body_func)

    def test_successful_methods(self):
        methods = list(self.app.SUPPORTED_METHODS)
        methods.remove("HEAD")
        for meth in methods:
            self.assert_body_is('request body', method=meth)

    def test_HEAD_method(self):
        self.assert_body_is('', method="HEAD")

    def test_failed_methods(self):
        for meth in self.app.SUPPORTED_METHODS:
            self.assert_not_found(path='/somebadpath')


class TestHeadFallback(HobokenTestCase):
    def after_setup(self):
        @self.app.get('/')
        def get_func():
            self.app.response.headers['X-Custom-Header'] = b'foobar'
            return 'get body'

    def test_HEAD_fallback(self):
        r = Request.build('/')
        r.method = "HEAD"
        resp = r.get_response(self.app)

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.body), 0)
        self.assertEqual(resp.headers['X-Custom-Header'], b'foobar')


# Load our list of test cases from our yaml file.
curr_dir = os.path.abspath(os.path.dirname(__file__))
test_file = os.path.join(curr_dir, 'routing_tests.yaml')
with open(test_file, 'rb') as f:
    file_data = f.read()
test_cases = list(yaml.load_all(file_data))


class TestRouting(object):
    @pytest.mark.parametrize('param', test_cases)
    def test_route(self, param):
        if 'skip' in param:
            if hasattr(unittest, 'SkipTest'):
                raise unittest.SkipTest(param['skip'])
            return

        matcher = Matcher(param['path'])
        regex = param['regex'].encode('latin-1')
        assert matcher.match_re.pattern == regex

        class FakeRequest(object):
            path_info = None

        for succ in param.get('successes', []):
            r = FakeRequest()
            r.path_info = succ['route'].encode('latin-1')
            matched, args, kwargs = matcher.match(r)

            expected_args = [x.encode('latin-1') for x in succ.get('args', [])]
            expected_kwargs_str = succ.get('kwargs', {})
            expected_kwargs = {}
            for k, v in iteritems(expected_kwargs_str):
                if isinstance(v, text_type):
                    v = v.encode('latin-1')
                expected_kwargs[k] = v
            assert matched is True
            assert args == expected_args
            assert kwargs == expected_kwargs

        for fail in param.get('failures', []):
            r = FakeRequest()
            r.path = fail
            matched, _, _ = matcher.match(r)

            assert matched is False


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMethods))
    suite.addTest(unittest.makeSuite(TestHeadFallback))
    # suite.addTest(unittest.makeSuite(TestRouting))

    return suite

