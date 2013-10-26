import sys
import warnings

# Import all of these modules so the generate methods get added onto the
# original extactor classes
from . import wrappedtype
from . import mappedtype
from . import typedef
from . import variable
from . import function
from . import enum
from . import pycode

from .base import CppScope

from .. import extractors
from ..generators import nci

class Module(CppScope):
    def __init__(self, module):
        super(Module, self).__init__(None)
        self.item = module

        self.module = self

        self.name = module.name
        self.pyname = module.name
        self.scopeprefix = ''
        self.cscopeprefix = ''
        self.pyscopeprefix = self.name + '.'

        self.pyitems = []

        # Items will add themselves to the items list as they're generated
        for item in module.items:
            item.generate(self)

        self.pyitems.sort(key=lambda item: item.order if item.order is not None
                                                      else sys.maxint)

    def setup(self, imported_modules):
        self.imported_modules = imported_modules

        self.setup_types()
        self.setup_objects()

    def gettype(self, name):
        type = super(Module, self).gettype(name)
        if type is not None:
            return type

        for mod in self.imported_modules:
            type = mod.gettype(name)
            if type is not None:
                self.typescache[name] = type
                return type

        return None

    def new_opaque_type(self, name):
        warnings.warn("Encountered unknown type '%s'. Creating opaque type"
                        % name)
        c = extractors.ClassDef(name=name)
        # XXX Is it a good idea to always place an opaque type in the global
        #     scope?
        c.generate(self)
        # TODO: Maybe the generate method should return the new object so this
        #       extra lookup isn't needed?
        self.gettype(name).setup()

    # TODO: change how cppCode/headerCode/etc are handled. It would be more
    #       memory efficient to delay loading them until they are about to be
    #       printed and deleted immediately after. This will likely be part of
    #       splitting individual classes into their own translation units.
    def write_files(self, pyfile, userpyfile, cppfile, hfile, verify_args):
        hfile.write(nci("""\
        #ifndef INCLUDE_GUARD_{0}s_H
        #define INCLUDE_GUARD_{0}s_H""".format(self.name)))

        for line in getattr(self.item, 'headerCode'):
            hfile.write(nci(line))

        for item in self.item.items:
            for line in getattr(item, 'headerCode', []):
                hfile.write(nci(line))
        for mod in self.item.imports:
            hfile.write('#include "%s.h"\n' % mod)

        self.print_nested_headercode(hfile)
        hfile.write("#endif")

        cppfile.write(nci("""\
        #include <cstring>
        #include <wrapper_lib.h>

        #include "{0}.h"
        """.format(self.name)))

        for line in self.item.cppCode:
            cppfile.write(nci(line))

        # TODO: Create the types-api object in this function
        # TODO: Does this need to have a module specfic name?
        initfunc = 'cffiinitcode_%s' % (self.item.name)
        cppfile.write(nci("""\
        extern "C" void %s()
        {
        """ % initfunc))
        # Lump all of the init code types together; their order shouldn't
        # matter for this generator
        for attr in ('initializerCode', 'preInitializerCode',
                     'postInitializerCode'):
            for line in getattr(self.item, attr):
                cppfile.write(nci(line, 4))
        cppfile.write('}\n')

        self.print_nested_cppcode(cppfile)

        # Write Python preamble
        pyfile.write(nci("""\
        import __builtin__
        import sys
        import cffi
        import types
        import numbers
        import collections

        import wrapper_lib

        {0} = sys.modules[__name__]""".format(self.name)))
        for module in self.item.imports:
            pyfile.write("import %s\n" % module)

        # Write cdefs
        pyfile.write(nci("""\
        ffi = cffi.FFI()
        ffi.cdef('''
        void* malloc(size_t);
        void free(void*);"""))

        # These typedefs don't go in the cdefs string because we don't
        # want them included in the verify code too.
        #for typedef in self.module.items:
        #    if (not isinstance(typedef, extractors.TypedefDef) or
        #        not typedef.platformDependent):
        #        continue
        #    pyfile.write("typedef %s %s;\n" % (typedef.type, typedef.name))

        self.print_nested_cdef(pyfile)

        pyfile.write(nci("""\
        ''')
        cdefs = ('''
        extern void (*WL_ADJUST_REFCOUNT)(void *, int);
        extern char **WL_EXCEPTION_NAME;
        extern char **WL_EXCEPTION_STRING;

        void %s(void);""" % initfunc))
        #for line in self.item.cdefs_cffi:
        #    pyfile.write(nci(line))
        #for klass in self.classes:
        #    self.printClassCDefs(klass, pyfile)
        #for mType in self.mappedTypes:
        #    self.printMappedTypeCDef(mType, pyfile)
        #dispatchItems(self.dispatchCDefs, self.globalItems, pyfile)
        self.print_nested_cdef_and_verify(pyfile)

        pyfile.write(nci("""\
        ''')
        ffi.cdef(cdefs)
        clib = ffi.verify(cdefs, %s)
        del cdefs

        wrapper_lib.populate_clib_ptrs(clib)
        clib.%s()""" % (self.build_verify_args(verify_args), initfunc)))

        for type in self.types:
            type.print_pycode(pyfile)
        for obj in self.objects:
            obj.print_pycode(pyfile)
        for scope in self.subscopes.itervalues():
            scope.print_pycode(pyfile)

        for item in self.pyitems:
            item.print_pycode(userpyfile)


        # Print classes' C++ bodies, before any method bodies are printed
        #for klass in self.classes:
        #    self.printClassCppBody(klass, hfile, cppfile)

        #for mType in self.mappedTypes:
        #    self.printMappedType(mType, pyfile, cppfile, 0)

        # Print classes' Python bodies and items
        #for klass in self.classes:
        #    self.printClass(klass, pyfile, cppfile)

        # Print global items
        #dispatchItems(self.dispatchPrint, self.globalItems, pyfile, cppfile)

        # Print Python finalization code (finalize multimethods, etc)
        #for klass in self.classes:
        #    self.printClassFinalization(klass, pyfile)
        #dispatchItems(self.dispatchFinalize, self.globalItems, pyfile)

        # Print Py*Defs (globals first)
        #dispatchItems(self.dispatchPrintPyDefs, self.pyItems, userPyfile, 0)
        #for klass in self.classes:
        #    self.printClassPyDefs(klass, userPyfile)

    def build_verify_args(self, verify_args):
        args = []
        for key, value in verify_args.iteritems():
            if isinstance(value, str):
                value = repr(value)
            else:
                value = '[%s]' % ', '.join([repr(i) for i in value])
            args.append("%s=%s" % (key, value))
        return ', '.join(args)
