import os
import yaml
import tempfile
from hoboken.tests.compat import unittest
import mock

from hoboken.config import ConfigProperty, ConfigDict
from hoboken.six import text_type


class TestConfigProperty(unittest.TestCase):
    def setUp(self):
        conv = mock.MagicMock()
        conv.return_value = 'conv_prop'

        class TestClass(object):
            config = mock.MagicMock()

            prop = ConfigProperty('prop')
            conv_prop = ConfigProperty('conv_prop', converter=conv)

        self.c = TestClass()
        self.conv = conv

    def test_setting(self):
        self.c.prop = 'foobar'
        self.c.config.__setitem__.assert_called_once_with('prop', 'foobar')

    def test_getting(self):
        self.c.prop
        self.c.config.__getitem__.assert_called_once_with('prop')

    def test_converter(self):
        self.c.config.__getitem__.return_value = 'foobar'
        self.c.conv_prop
        self.conv.assert_called_once_with('foobar')


class TestConfigDict(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.c = ConfigDict(self.d)
        self.f = tempfile.NamedTemporaryFile(dir=self.d)

    def write(self, val):
        if isinstance(val, text_type):
            val = val.encode('utf-8')
        self.f.write(val)
        self.f.flush()

    def test_from_object(self):
        class Test(object):
            not_set = 1
            Not_set = 2
            IS_SET  = 3

        t = Test()
        self.c.from_object(t)

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_dict(self):
        d = {
            'not_set': 1,
            'Not_set': 2,
            'IS_SET':  3,
        }

        self.c.from_dict(d)

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_json(self):
        j = '{"not_set": 1, "IS_SET": 3, "Not_set": 2}'
        self.write(j)

        self.c.from_json(self.f.name)

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_json_invalid(self):
        self.write('foobar::asdf')

        self.assertFalse(self.c.from_json(self.f.name, silent=True))

        with self.assertRaises(ValueError):
            self.c.from_json(self.f.name, silent=False)

        self.assertFalse(self.c.from_json('invalid_name', silent=True))

        with self.assertRaises(IOError):
            self.c.from_json('invalid_name', silent=False)

    def test_from_yaml(self):
        y = """
not_set: 1
Not_set: 2
IS_SET: 3
        """
        self.write(y)

        self.c.from_yaml(self.f.name)

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_yaml_invalid(self):
        self.write('foobar: asdf\nanother: {')

        self.assertFalse(self.c.from_yaml(self.f.name, silent=True))

        with self.assertRaises(yaml.YAMLError):
            self.c.from_yaml(self.f.name, silent=False)

        self.assertFalse(self.c.from_yaml('invalid_name', silent=True))

        with self.assertRaises(IOError):
            self.c.from_yaml('invalid_name', silent=False)

    def test_from_pyfile(self):
        py = """
not_set = 1
Not_set = 2
IS_SET = 3
        """
        self.write(py)

        self.c.from_pyfile(self.f.name)

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_pyfile_invalid(self):
        self.assertFalse(self.c.from_pyfile('invalid_name', silent=True))

        with self.assertRaises(IOError):
            self.c.from_pyfile('invalid_name', silent=False)

    def test_from_envvar(self):
        py = """
not_set = 1
Not_set = 2
IS_SET = 3
        """
        self.write(py)
        os.environ['MY_ENVIRONMENT_VAR'] = self.f.name

        self.c.from_envvar('MY_ENVIRONMENT_VAR')

        self.assertIn('IS_SET', self.c)
        self.assertNotIn('not_set', self.c)
        self.assertNotIn('Not_set', self.c)

    def test_from_envvar_invalid(self):
        self.assertFalse(self.c.from_envvar('INVALID_ENV_VAR', silent=True))

        with self.assertRaises(RuntimeError):
            self.assertFalse(self.c.from_envvar('INVALID_ENV_VAR', silent=False))



def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestConfigProperty))
    suite.addTest(unittest.makeSuite(TestConfigDict))

    return suite
