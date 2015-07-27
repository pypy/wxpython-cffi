import io
import sys
import warnings

# Import all of these modules so the generate methods get added onto the
# original extactor classes
from . import wrappedtype
from . import mappedtype
from . import typedef
from . import variable
from . import function
from . import property
from . import membervar
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
        self._cffi_name = '_cffi' + self.name

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

        import cffi

        self.ffi = cffi.FFI()
        for module in self.imported_modules:
            self.ffi.include(module.ffi)
        cdefs = io.BytesIO()
        self.print_nested_cdef(cdefs)
        self.ffi.cdef(cdefs.getvalue())
        self.ffi.cdef('\n'.join(self.item.cdefs_cffi))

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
        # XXX This is another place where manipulation of the input data is
        #     happening. Maybe creating a OpaqueType class is needed? That
        #     would probably duplicate functionality from WrappedType though...
        c = extractors.ClassDef(name=name, opaqueType=True)
        # XXX Is it a good idea to always place an opaque type in the global
        #     scope? What's the alternative, making tons of opaque types with
        #     the same name in different scopes?
        c.generate(self).setup()

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
        hfile.write("#endif  /* INCLUDE_GUARD */")
        hfile.flush()

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
        cppfile.flush()

        # Write Python preamble
        pyfile.write(nci("""\
        import __builtin__
        import sys
        import types
        import numbers
        import collections

        import wrapper_lib

        {0} = sys.modules[__name__]""".format(self.name)))
        for module in self.item.imports:
            pyfile.write("import %s\n" % module)

        self.ffi.cdef('''
        void* malloc(size_t);
        void free(void*);
        ''')

        cdefs = io.BytesIO()
        cdefs.write('''
        extern void (*WL_ADJUST_REFCOUNT)(void *, int);
        extern char **WL_EXCEPTION_NAME;
        extern char **WL_EXCEPTION_STRING;

        void %s(void);''' % initfunc)

        self.print_nested_cdef_and_verify(cdefs)

        self.ffi.cdef(cdefs.getvalue())

        source = ['#include <stdlib.h>']
        source.extend(self.item.cdefs_cffi)
        for module in self.imported_modules:
            source.extend(module.item.cdefs_cffi)
        source.append(cdefs.getvalue())
        self.ffi.set_source(
            self._cffi_name,
            '\n'.join(source),
            **verify_args)

        pyfile.write(nci("""\
        from %s import ffi, lib as clib
        wrapper_lib.populate_clib_ptrs(clib)
        clib.%s()
        """ % (self._cffi_name, initfunc)))

        for obj in self.print_order:
            obj.print_pycode(pyfile)

        for type in self.types:
            type.print_pycode(pyfile)
        for obj in self.objects:
            obj.print_pycode(pyfile)
        for scope in self.subscopes:
            scope.print_pycode(pyfile)

        for item in self.pyitems:
            item.print_pycode(userpyfile)

        for type in self.types:
            type.print_finalize_pycode(pyfile)

        self.ffi.compile('cffi')

    def build_verify_args(self, verify_args):
        args = []
        for key, value in verify_args.iteritems():
            if isinstance(value, str):
                value = repr(value)
            else:
                value = '[%s]' % ', '.join([repr(i) for i in value])
            args.append("%s=%s" % (key, value))
        return ', '.join(args)
