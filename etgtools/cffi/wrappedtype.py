from . import utils
from .base import CppType, CppScope

from .. import extractors
from ..generators import nci

def create_wrappedtype(mtype, parent):
    WrappedType(mtype, parent)
extractors.ClassDef.generate = create_wrappedtype

class WrappedType(CppScope, CppType):
    def __init__(self, cls, parent):
        CppType.__init__(self, cls, parent)
        CppScope.__init__(self, parent)

        self.scopeprefix = parent.scopeprefix + self.name + '::'
        self.cscopeprefix = parent.cscopeprefix + self.pyname + '_88_'
        self.pyscopeprefix = parent.pyscopeprefix + self.pyname + '.'

        self.convert_pyobj_code = getattr(cls, 'convertFromPyObject_cffi', None)
        self.convert_pyobj_isinstance_code = getattr(cls, 'instancecheck', None)
        self.convert_subclass_code = getattr(cls, 'detectSubclassCode_cffi', None)

        self.allownone = self.item.allowNone
        # No matter what, this class cannot be instantiated from Python
        self.uninstantiable = self.item.abstract

        self.virtualmethods = []
        self.protectedmethods = []

        for klass in cls.innerclasses:
            WrappedType(klass, self)

    def setup_types(self):
        self.setup()

    @utils.call_once
    def setup(self):
        if isinstance(self.parent, WrappedType):
            # If this is a nested class, always setup the outer class first so
            # that this class will appear before any of its subclasses in the
            # Python file
            self.parent.setup()

        self.bases = []
        for basename in self.item.bases:
            base = self.parent.gettype(basename)
            if base is None:
                raise ValueError("Unable to locate base class '%s' for class "
                                 "'%s'" % (basename, self.name))
            base.setup()
            self.bases.append(base)

        super(WrappedType, self).setup_types()
        super(WrappedType, self).setup_objects()

        self.pickup_base_virtuals()
        self.purevirtualabstract = any(m.purevirtual for m in self.virtualmethods)

        if len(self.virtualmethods) > 0 or len(self.protectedmethods) > 0:
            self.cppnname = 'cfficlass' + self.cname
            self.hassubclass = True
        else:
            self.cppname = self.name
            self.hassubclass = False

        self.parent.append_to_printing_order(self)

    def pickup_base_virtuals(self):
        for base in self.bases:
            # Look at every virtual method in the base and see if it has been
            # reimplemented in this class. If not, add it to the virtuals list.
            for vmeth in base.virtualmethods:
                if vmeth not in self.virtualmethods:
                    # TODO: do I want to duplicate the virtual method here?
                    self.virtualmethods.append(vmeth.copy(self))

    def gettype(self, name):
        type = super(WrappedType, self).gettype(name)
        if type is not None:
            return type

        # Check for the type in base classes too
        for base in self.bases:
            type = base.gettype(name)
            if type is not None:
                return type

        return None

    def build_typeinfo(self, typeinfo):
        typeinfo.c_type = self.unscopedname + ' *'
        typeinfo.cdef_type = 'void *'
        typeinfo.c_virt_return_type = self.unscopedname + ' *'
        typeinfo.cdef_virt_return_type = 'void *'

        if not (typeinfo.ptrcount or typeinfo.refcount):
            # Functions that return wrapped types by value will return via a
            # pointer parameter
            typeinfo.c_virt_return_type = 'void'
            typeinfo.cdef_virt_return_type = 'void'

        if typeinfo.const:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        pytypes = [self.unscopedpyname]
        #if self.convertcode is not None:
        if hasattr(self.item, 'convertFromPyObject_cffi'):
            pytypes.append('{0}._pyobject_mapping_'.format(
                self.unscopedpyname))
        if typeinfo.ptrcount or self.allownone:
            pytypes.append('types.NoneType')
        typeinfo.py_type = '(' + ', '.join(pytypes) + ')'

        if not typeinfo.flags.inout and (typeinfo.ptrcount == 2 or
           typeinfo.refcount and typeinfo.ptrtype):
            typeinfo.flags.out = True

        if typeinfo.flags.out or typeinfo.flags.inout:
            typeinfo.c_type += '*'
            typeinfo.cdef_type += '*'

        if typeinfo.flags.array:
            typeinfo.c_type += ' *'
            typeinfo.cdef_type += '[]'

            arg = ', ctype="%s"' % typeinfo.cdef_type
            typeinfo.py_type = ("wrapper_lib.create_array_type(%s%s)" %
                                (self.unscopedpyname, arg))

        typeinfo.c_virt_type = typeinfo.c_type
        typeinfo.cdef_virt_type = typeinfo.cdef_type

    def print_cdef(self, pyfile):
        if not self.uninstantiable and len(self.virtualmethods) > 0:
                                                     
            pyfile.write(nci("""\
            void(*{0.cname}_vtable[{1}])(void);
            void {0.cname}_set_flag(void *, int);
            void {0.cname}_set_flags(void *, char*);
            """.format(self, len(self.virtualmethods))))
        if self.convert_subclass_code is not None:
            pyfile.write("char * cffigetclassname_%s(void *);\n" %
                         self.cname)

        # TODO: detect private assign op and private copy ctor better
        #if (not klass.privateAssignOp and not klass.privateCopyCtor and
        #    not klass.abstract):
        #    print >> pyfile, ("void {0}{1}(void*, void*);"
        #                      .format(ASSIGN_PREFIX, klass.name))

    @utils.call_once
    def print_pycode(self, pyfile, indent=0):
        if self.uninstantiable:
            pyfile.write(nci("@wrapper_lib.abstract_class", indent))

        elif any(b.uninstantiable or b.purevirtualabstract for b in self.bases):
            pyfile.write(nci("@wrapper_lib.concrete_subclass", indent))

        elif self.purevirtualabstract:
            pyfile.write(nci("@wrapper_lib.purevirtual_abstract_class", indent))

        bases = ', '.join([b.unscopedpyname for b in self.bases])
        if bases == '':
            bases = 'wrapper_lib.CppWrapper'
        pyfile.write(nci("class %s(%s):" % (self.pyname, bases), indent))

        # TODO: remove this once classes are actually printed
        pyfile.write(nci('pass', indent + 4))


        # Print class members that are picked up by the metaclass
        if not self.uninstantiable and len(self.virtualmethods) > 0:
            pyfile.write(nci("""\
            _vtable = clib.{0}_vtable

            def _set_vflag(self, i):
                clib.{0}_set_flag(wrapper_lib.get_ptr(self), i)

            def _set_vflags(self, flags):
                clib.{0}_set_flags(wrapper_lib.get_ptr(self), flags)
            """.format(self.cname), indent + 4))

        if self.convert_subclass_code is not None:
            pyfile.write(nci('_get_cpp_classname_ = clib.cffigetclassname_%s' %
                             self.cname, indent + 4))

        if self.convert_pyobj_code is not None:
            pyfile.write(nci("""\
            class _pyobject_mapping_(object):
                __metaclass__ = wrapper_lib.MMTypeCheckMeta
            """, indent + 4))

            pyfile.write(nci("""\
            @staticmethod
            def __instancecheck__(py_obj):""", indent + 8))
            pyfile.write(nci(self.convert_pyobj_isinstance_code, indent + 12))

            nonetest = '' if self.allownone else 'py_obj is None or '
            pyfile.write(nci("""\
            @staticmethod
            def convert(py_obj):
                if {0}issubclass(type(py_obj), {1}):
                    return py_obj
            """.format(nonetest, self.unscopedpyname), indent + 8))
            pyfile.write(nci(self.convert_pyobj_code
                            .format(PYNAME=self.unscopedpyname), indent + 12))

        # Print nested items
        for obj in self.objects:
            obj.print_pycode(pyfile, indent + 4)
        for type in self.types:
            type.print_pycode(pyfile, indent + 4)
        for scope in self.subscopes.itervalues():
            scope.print_pycode(pyfile, indent + 4)

    def print_cppcode(self, cppfile):
        if len(self.virtualmethods) > 0 and not self.uninstantiable:
            cppfile.write(nci("""\
            WL_INTERNAL void(*{0.cname}_vtable[{1}])();

            WL_INTERNAL void {0.cname}_set_flag({0.cppname} *self, int i)
            {{
                self->vflags[i] = 1;
            }}

            WL_INTERNAL void {0.cname}_set_flags({0.cppname} *self, char *flags)
            {{
                memcpy(self->vflags, flags, sizeof(self->vflags));
            }}""".format(self, len(self.virtualMethods))))

        if self.convert_subclass_code is not None:
            cppfile.write(nci("""\
            WL_INTERNAL const char * cffigetclassname_{0.cname}({0.cppname} *cpp_obj)
            {{""".format(self)))
            cppfile.write(nci(self.convert_subclass_code, 4))
            cppfile.write("}\n")

    def call_cpp_param_setup(self, typeinfo, name):
        pass

    def call_cpp_param_inline(self, typeinfo, name):
        pass

    def call_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_param_setup(self, typeinfo, name):
        pass

    def virt_cpp_param_inline(self, typeinfo, name):
        pass

    def virt_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_return_setup(self, typeinfo, name):
        pass

    def virt_cpp_return_cleanup(self, typeinfo, name):
        pass

    def convert_variable_cpp_to_c(self, typeinfo, name):
        # Always pass wrapped classes as pointers. If this is by value or
        # a const reference, it needs to be copy constructored onto the
        # heap, with Python taking ownership of the new object.
        if typeinfo.ptrcount:
            return name
        elif typeinfo.refcount and (not typeinfo.const or
             typeinfo.flags.nocopy or not self.uninstantiable or
             not self.purevirtualabstract):
            return '&' + name
        else:
            return "new %s(%s)" % (self.cppname, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        pass
