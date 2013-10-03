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
    def __init__(self, module_name, path_pattern):
        with open(path_pattern % module_name, 'rb') as f:
            main_module = pickle.load(f)
        self.name = self.module.name
        self.completed = False

        for mod in main_module.includes:
            with open(path_pattern % mod, 'rb') as f:
                mod = pickle.load(f)
                for attr in ('headerCode', 'cppCode', 'initializerCode',
                             'preInitializerCode', 'postInitializerCode',
                             'includes', 'imports', 'items', 'cdefs_cffi'):
                    getattr(main_module, attr).extend(getattr(mod, attr))
        self.module = Module(main_module)

    def generate(self, generators):
        if self.completed is True:
            return
        self.completed = True

        # Build a list of the generators for modules we're importing. We will
        # need this to lookup C++ classes that come from the imported modules
        self.module.imports = set(self.module.imports)
        self.imports = []
        for import_name in self.module.imports:
            self.imports.append(generators[import_name])
            generators[import_name].init(generators)

        module.setup()

    def write_files(self, pyfile, userpyfile, cppfile, hfile, verify_args):
        pass
