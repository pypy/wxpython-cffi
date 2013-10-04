import cPickle as pickle
import cStringIO
import warnings

from module import Module

class LiteralVerifyArg(str):
    """
    A string type than when used as in verifyArgs won't be wrapped in quotes.
    """
    def __repr__(self): return self

class BindingGenerator(object):
    # TODO: maybe I want defdir instead of path_pattern?
    def __init__(self, path_pattern):
        self.path_pattern = path_pattern
        self.modules = { }

    def generate(self, module_name):
        if module_name in self.modules:
            return

        with open(self.path_pattern % module_name, 'rb') as f:
            module = pickle.load(f)

        for mod in module.includes:
            with open(path_pattern % mod, 'rb') as f:
                mod = pickle.load(f)
                for attr in ('headerCode', 'cppCode', 'initializerCode',
                             'preInitializerCode', 'postInitializerCode',
                             'includes', 'imports', 'items', 'cdefs_cffi'):
                    getattr(module, attr).extend(getattr(mod, attr))

        imported_modules = []
        for mod in module.imports:
            self.generate(mod)
            imported_modules.append(self.modules[mod])

        module = Module(module)
        self.modules[module.name] = module
        module.setup(imported_modules)

    def write_files(self, module_name, pyfile, userpyfile, cppfile, hfile,
                    verify_args):
        pass
