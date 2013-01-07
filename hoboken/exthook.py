import imp
import sys


class ImportRedirector(object):
    def __init__(self, base_name, replace_pattern, builtins=None):
        self.base_name = base_name
        self.replace_pattern = replace_pattern
        self.builtins = builtins

        # This makes unit-testing easier.
        self.import_func = __import__

        # Create a module.
        self.module = sys.modules.setdefault(base_name,
                                             imp.new_module(base_name))
        self.module.__dict__.update({
            '__file__': __file__,
            '__path__': [],
            '__all__': [],
            '__loader__': self
        })

        # Make ourselves an import hook.
        sys.meta_path.append(self)

    def find_module(self, fullname, path=None):
        # If there's no dots, this can't be an extension module.
        if '.' not in fullname:
            return

        # Find the module name, make sure the base is ourselves.
        base, modname = fullname.rsplit('.', 1)
        if base != self.base_name:
            return

        # If we get here, we can handle this module.
        return self

    def load_module(self, fullname):
        # If this module is already loaded, return it.
        if fullname in sys.modules:
            return sys.modules[fullname]

        # Get the module name after the last '.'
        base, modname = fullname.rsplit('.', 1)
        module = None

        # Check if we have a builtin module with this name.
        if self.builtins is not None:
            try_name = self.builtins + '.' + modname
            try:
                self.import_func(try_name)
                module = sys.modules[try_name]
            except ImportError:
                # TODO: borrow from Flask to check if we failed to import this
                # module, or some submodule.
                pass

        # If we don't have a module, we try our new import.
        if module is None:
            # Get the name to import and import it.
            realname = self.replace_pattern % modname
            self.import_func(realname)
            module = sys.modules[realname]

        # Store the module in sys.modules, now that we have it.
        sys.modules[fullname] = module

        # Save the module on our extension module, and return it.
        setattr(self.module, modname, module)
        module.__loader__ = self
        return module
