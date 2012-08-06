from . import HobokenTestCase, skip, hoboken
import os
import yaml
import unittest
from .helpers import parametrize, parameters
from webob import Request

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
            self.app.response.headers['X-Custom-Header'] = 'foobar'
            return 'get body'

    def test_HEAD_fallback(self):
        r = Request.blank('/')
        r.method = "HEAD"
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_int, 200)
        self.assert_equal(len(resp.body), 0)
        self.assert_equal(resp.headers['X-Custom-Header'], 'foobar')


# Load our list of test cases from our yaml file.
curr_dir = os.path.abspath(os.path.dirname(__file__))
test_file = os.path.join(curr_dir, 'routing_tests.yaml')
with open(test_file, 'rb') as f:
    file_data = f.read()
test_cases = list(yaml.load_all(file_data))

def make_name(idx, param):
    return "test_" + param['name']

@parametrize
class TestRouting(HobokenTestCase):
    @parameters(test_cases, name_func=make_name)
    def test_route(self, param):
        if 'skip' in param:
            if hasattr(unittest, 'SkipTest'):
                raise unittest.SkipTest(param['skip'])
            return

        matcher = Matcher(param['path'])
        regex = param['regex']
        self.assert_equal(matcher.match_re.pattern, regex)

        class FakeRequest(object):
            path_info = None

        for succ in param.get('successes', []):
            r = FakeRequest()
            r.path_info = succ['route']
            matched, args, kwargs = matcher.match(r)

            expected_args = succ.get('args', [])
            expected_kwargs = succ.get('kwargs', {})
            self.assert_equal(matched, True)
            self.assert_equal(args, expected_args)
            self.assert_equal(kwargs, expected_kwargs)

        for fail in param.get('failures', []):
            r = FakeRequest()
            r.path = fail
            matched, _, _ = matcher.match(r)

            self.assert_equal(matched, False)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestMethods))
    suite.addTest(unittest.makeSuite(TestHeadFallback))
    suite.addTest(unittest.makeSuite(TestRouting))

    return suite

