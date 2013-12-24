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
        self.modules[module_name].write_files(pyfile, userpyfile, cppfile,
                                              hfile, verify_args)


    """
    def __init__(self, module_name, path_pattern):
        with open(path_pattern % module_name, 'rb') as f:
            main_module = pickle.load(f)
        self.name = main_module.name
        self.completed = False

        for mod in main_module.includes:
            with open(path_pattern % mod, 'rb') as f:
                mod = pickle.load(f)
                for attr in ('headerCode', 'cppCode', 'initializerCode',
                             'preInitializerCode', 'postInitializerCode',
                             'includes', 'imports', 'items', 'cdefs_cffi'):
                    getattr(main_module, attr).extend(getattr(mod, attr))

        self.imported_modules = set(main_module.imports)
        self.module = Module(main_module)
        TypeInfo.clearCache()

    def generate(self, generators):
        if self.completed is True:
            return
        self.completed = True

        # Build a list of the generators for modules we're importing. We will
        # need this to lookup C++ classes that come from the imported modules
        imported_modules = []
        for import_name in self.imported_modules:
            self.imports.append(generators[import_name].module)

        module.setup(imported_modules)
    """
