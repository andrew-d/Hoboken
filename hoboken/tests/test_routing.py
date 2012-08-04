from . import HobokenTestCase, skip, hoboken
import os
import yaml
import unittest
from .helpers import parametrize, parameters
from webob import Request

Matcher = hoboken.matchers.HobokenRouteMatcher


# Some useful tests from Sinatra: https://github.com/sinatra/sinatra/blob/master/test/routing_test.rb


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
        def get_func(req, resp):
            resp.headers['X-Custom-Header'] = 'foobar'
            return 'get body'

    def test_HEAD_fallback(self):
        r = Request.blank('/')
        r.method = "HEAD"
        resp = r.get_response(self.app)

        self.assert_equal(resp.status_int, 200)
        self.assert_equal(len(resp.body), 0)
        self.assert_equal(resp.headers['X-Custom-Header'], 'foobar')


@skip("Since webob insists on unescaping encoded slashes")
class TestEncodedSlashes(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/:param")
        def echo_func(req, resp):
            return req.urlvars['param']

    def test_slashes(self):
        self.assert_body_is("foo/bar", path="/foo%2Fbar")


class TestSplatParams(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/*/foo/*/*")
        def echo_func(req, resp):
            return '\n'.join(req.urlargs)

    def test_exact_match(self):
        self.assert_body_is("one\ntwo\nthree", path="/one/foo/two/three")

    def test_extended_match(self):
        self.assert_body_is("one\ntwo\nthree/four", path="/one/foo/two/three/four")

    def test_fails_properly(self):
        self.assert_not_found(path='/one/foo/two')


class TestMixedParams(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/:one/*")
        def test_func(req, resp):
            self.assert_equal(len(req.urlargs), 1)
            self.assert_equal(req.urlargs[0], "foo/bar")
            self.assert_equal(req.urlvars['one'], "two")
            return 'foo'

    def test_mixed_params_simple(self):
        self.assert_body_is("foo", path='/two/foo/bar')


class TestDotsInParams(HobokenTestCase):
    def after_setup(self):
        @self.app.get("/:foo/:bar")
        def echo_func(req, resp):
            return req.urlvars['foo'] + '\n' + req.urlvars['bar']

        @self.app.get("/:foo.:bar")
        def echo_func2(req, resp):
            return req.urlvars['foo'] + '\n' + req.urlvars['bar']

    def test_complex_param(self):
        self.assert_body_is("test@foo.com\njohn", path='/test@foo.com/john')

    def test_dot_outside_param(self):
        self.assert_body_is("foo\nbar", path='/foo.bar')

    def test_dot_outside_param_fails(self):
        self.assert_not_found(path="/foo1bar")


class TestMiscellaneousCharacters(HobokenTestCase):
    TEST_CHARS = '$()"\''

    def after_setup(self):
        for char in self.TEST_CHARS:
            path = '/test' + char + '/'
            self.app.add_route('GET', path, self.body_func)

    def test_chars(self):
        for char in self.TEST_CHARS:
            path = '/test' + char + '/'
            self.assert_body_is('request body', path=path)

    def test_chars_fail_properly(self):
        self.assert_not_found(path='/test/')


class TestPlusCharacter(HobokenTestCase):
    def after_setup(self):
        self.app.add_route("GET", '/te+st', self.body_func)

    def test_plus_matches(self):
        self.assert_body_is("request body", path='/te%2Bst')

    def test_plus_fails_when_expected(self):
        self.assert_not_found(path='/test')


class TestSpaceCharacter(HobokenTestCase):
    def after_setup(self):
        self.app.add_route('GET', '/path with spaces', self.body_func)

        @self.app.get("/:foo")
        def echo_func(req, resp):
            return req.urlvars["foo"]

    @skip("Not sure if this is expected behavior")
    def test_space_decodes_to_plus(self):
        self.assert_body_is('te st', path='/te+st')

    def test_plus_matches_space(self):
        self.assert_body_is("request body", path='/path+with+spaces')

    def test_percent_encoded_spaces(self):
        self.assert_body_is("request body", path="/path%20with%20spaces")

    def test_bad_path_fails(self):
        self.assert_not_found("/foo/bar/bad/path")


class TestInvalidRoutes(HobokenTestCase):
    """TODO: Test routes that don't match, in various interesting configurations"""
    pass


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
            path = None

        for succ in param['successes']:
            r = FakeRequest()
            r.path = succ['route']
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
    suite.addTest(unittest.makeSuite(TestEncodedSlashes))
    suite.addTest(unittest.makeSuite(TestSplatParams))
    suite.addTest(unittest.makeSuite(TestMixedParams))
    suite.addTest(unittest.makeSuite(TestDotsInParams))
    suite.addTest(unittest.makeSuite(TestMiscellaneousCharacters))
    suite.addTest(unittest.makeSuite(TestPlusCharacter))
    suite.addTest(unittest.makeSuite(TestSpaceCharacter))
    suite.addTest(unittest.makeSuite(TestInvalidRoutes))
    suite.addTest(unittest.makeSuite(TestRouting))

    return suite

