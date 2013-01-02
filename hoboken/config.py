import os
import imp
import json
import errno

try:
    import yaml
except ImportError:
    yaml = None

from hoboken.six import exec_, iteritems


class ConfigProperty(object):
    """
    This class will proxy an attribute to the object's config dict.
    """
    def __init__(self, name, converter=None):
        self.name = name
        self.converter = converter

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        ret = obj.config[self.name]
        if self.converter is not None:
            ret = self.converter(ret)

        return ret

    def __set__(self, obj, value):
        obj.config[self.name] = value


class ConfigDict(dict):
    """
    This class is a dictionary with a few extra methods that allow populating
    it from alternate sources such as a Python file, object, JSON or YAML file.
    """
    def __init__(self, root_dir, defaults=None):
        dict.__init__(self, defaults or {})
        self.root_dir = root_dir

    def from_object(self, obj):
        """
        Populates this dictionary with values from a given object.  All upper-
        case attributes in the given object will be stored in this dictionary.
        """
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_dict(self, d):
        """
        Populates this dictionary with values from a given dictionary.  All
        upper-case root keys in the given dictionary are added to this object.
        """
        for key, val in iteritems(d):
            if key.isupper():
                self[key] = val

    def from_json(self, file, silent=False, **kwargs):
        """
        Populates this dictionary with values from a JSON config file.  The
        behavior of this function, with regards to loading keys, is identical
        to the from_dict() function.

        All kwargs to this function are passed to json.load().
        """
        file_path = os.path.join(self.root_dir, file)

        # Load and read the file.
        try:
            with open(file_path, 'r') as f:
                d = json.load(f, **kwargs)
        except ValueError:
            # JSON decoding error.  Ignore if silent.
            if silent:
                return False

            # Re-raise the error otherwise.
            raise

        except (IOError, OSError) as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False

            # Set a more descriptive message on our error.
            e.strerror = 'Unable to load JSON configuration ' \
                         'file (%s)' % e.strerror

            raise

        self.from_dict(d)
        return True

    if yaml is not None:
        def from_yaml(self, file, silent=False, **kwargs):
            """
            Populates this dictionary with values from a JSON config file.  The
            behavior of this function, with regards to loading keys, is identical
            to the from_dict() function.

            All kwargs to this function are passed to json.load().
            """
            file_path = os.path.join(self.root_dir, file)

            # Load and read the file.
            try:
                with open(file_path, 'rb') as f:
                    d = yaml.load(f, **kwargs)
            except yaml.YAMLError:
                # JSON decoding error.  Ignore if silent.
                if silent:
                    return False

                # Re-raise the error otherwise.
                # TODO: Do we want to re-raise as a ValueError?
                raise

            except (IOError, OSError) as e:
                if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                    return False

                # Set a more descriptive message on our error.
                e.strerror = 'Unable to load YAML configuration ' \
                             'file (%s)' % e.strerror

                raise

            self.from_dict(d)
            return True

    def from_pyfile(self, file, silent=False):
        """
        Populates this dictionary with values from a Python file.  Behavior
        of this function, with regards to loading keys, is identical to the
        from_object function called on the imported Python file.
        """
        file_path = os.path.join(self.root_dir, file)

        # We create a temporary module to load into.
        m = imp.new_module('config')
        m.__file__ = file

        try:
            with open(file_path, 'r') as f:
                exec_(f.read() + "\n", m.__dict__, m.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False

            e.strerror = 'Unable to load Python configuration' \
                         'file (%s)' % e.strerror
            raise

        self.from_object(m)
        return True

    def from_envvar(self, var, silent=False):
        """
        Populates this dictionary with values from a Python file pointed to by
        an environment variable.  This function effectively performs the
        following:

            config.from_pyfile(os.environ['ENVIRONMENT_VAR_NAME'])
        """
        ret = os.environ.get(var)
        if not ret:
            if silent:
                return False
            raise RuntimeError('The environment variable "%r" is not set, '
                               'and the config file could not be loaded.  '
                               'Please set this variable to a valid file '
                               'path to use as a configuration file.' %
                               var)

        return self.from_pyfile(ret, silent=silent)

    def __repr__(self):
        return "<%s %s>" % (self.__class__.__name__, dict.__repr__(self))

