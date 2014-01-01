from . import utils
from .base import CppType, CppScope

from .. import extractors
from ..generators import nci

def create_wrappedtype(mtype, parent, is_opaque=False):
    return WrappedType(mtype, parent, is_opaque)
extractors.ClassDef.generate = create_wrappedtype

class WrappedType(CppScope, CppType):
    def __init__(self, cls, parent, is_opaque=False):
        CppType.__init__(self, cls, parent)
        CppScope.__init__(self, parent)

        self.scopeprefix = parent.scopeprefix + self.name + '::'
        self.cscopeprefix = parent.cscopeprefix + self.pyname + '_88_'
        self.pyscopeprefix = parent.pyscopeprefix + self.pyname + '.'

        self.convert_pyobj_code = getattr(cls, 'convertFromPyObject_cffi', None)
        self.convert_pyobj_isinstance_code = getattr(cls, 'instanceCheck_cffi', None)
        self.convert_subclass_code = getattr(cls, 'detectSubclassCode_cffi', None)

        self.allownone = self.item.allowNone
        # No matter what, this class cannot be instantiated from Python
        self.uninstantiable = self.item.abstract

        self.virtualmethods = []
        self.protectedmethods = []

        self.to_c_array_name = 'WL_wrappedtype_array_to_c<%s>' % self.unscopedname
        self.to_cpp_array_name = 'WL_wrappedtype_array_to_cpp<%s>' % self.unscopedname

        self.docstring = utils.fix_docstring(cls.briefDoc)

        self.included_headers = self.item.includes

        for klass in cls.innerclasses:
            klass.generate(self)

        for item in cls.items:
            item.generate(self)

    @property
    def copy_ctor_visibility(self):
        from .function import CtorMethod
        for m in self.objects:
            if isinstance(m, CtorMethod) and m.iscopyctor():
                return m.protection
        # Every class should have a copy ctor.
        raise Exception()

    def is_superclass(self, other):
        return self is other or any(self.is_superclass(b) for b in other.bases)

    def setup_types(self):
        self.setup()

    def setup_objects(self):
        pass

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

        # Before we can start examining methods, they need to be setup
        super(WrappedType, self).setup_objects()

        self.setup_ctors()
        self.pickup_base_virtuals()
        self.purevirtualabstract = any(m.purevirtual for m in self.virtualmethods)

        if len(self.virtualmethods) > 0 or len(self.protectedmethods) > 0:
            self.cppname = 'cfficlass' + self.cname
            self.hassubclass = True
        else:
            self.cppname = self.unscopedname
            self.hassubclass = False

        # Add a dtor if the class doesn't already have one
        from .function import DtorMethod
        if not any(isinstance(m, DtorMethod) for m in self.objects):
            DtorMethod.new_std_dtor(self)

        super(WrappedType, self).setup_types()

        self.parent.append_to_printing_order(self)

    def setup_ctors(self):
        """Add a copy Ctor and a default Ctor, if possible."""
        hasanyctor = False
        hascopyctor = False
        from .function import CtorMethod
        for meth in self.objects:
            if not isinstance(meth, CtorMethod):
                continue

            hasanyctor = True
            hascopyctor = hascopyctor or meth.iscopyctor()


        if not hasanyctor:
            (extractors.MethodDef(name=self.name, isCtor=True)
             .generate(self)
             .setup())
        # Hypothetically, we should check for a private assignment operator
        # before generating the copy ctor, but I don't actually see the use
        # case for it.
        if not hascopyctor:
            # Search the bases to see if they have private copy ctors
            protection = 'public'
            if any(b.copy_ctor_visibility == 'private' for b in self.bases):
                protection = 'private'
            (extractors.MethodDef(
                name=self.name, isCtor=True, protection=protection,
                items=[extractors.ParamDef(type='const %s &' % self.name,
                                           name='other')])
             .generate(self)
             .setup())

    def pickup_base_virtuals(self):
        for base in self.bases:
            for vmeth in base.virtualmethods:
                # Check if the user has made a declaration hiding this method
                # (ie delcared a method with the same name.)
                if not any(m.name == vmeth.name for m in self.virtualmethods):
                    # If no method is declared hiding the one from the base
                    # class, copy each overload of the virtual method into the
                    # sub class.
                    for m in vmeth.overload_manager.functions:
                        m.copy_onto_subclass(self)

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

        if typeinfo.const:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        pytypes = [self.unscopedpyname]
        if self.convert_pyobj_code is not None:
            pytypes.append('{0}._pyobject_mapping_'.format(
                self.unscopedpyname))
        # Pointers and references with allownone are allowed to take Nones
        if typeinfo.ptrcount or self.allownone:
            pytypes.append('types.NoneType')
        typeinfo.py_type = '(' + ', '.join(pytypes) + ')'

        if not typeinfo.flags.inout and (typeinfo.ptrcount == 2 or
           typeinfo.refcount and typeinfo.ptrcount):
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

        typeinfo.wrapper_type = typeinfo.cpp_type.strip('&*') + '*'

        typeinfo.default_placeholder = 'ffi.NULL'

    def print_cdef_and_verify(self, pyfile):
        if not self.uninstantiable and len(self.virtualmethods) > 0:

            pyfile.write(nci("""\
            void(*{0.cname}_vtable[{1}])(void);
            void {0.cname}_set_flag(void *, int);
            void {0.cname}_set_flags(void *, char*);
            """.format(self, len(self.virtualmethods))))
        if self.convert_subclass_code is not None:
            pyfile.write("char * cffigetclassname_%s(void *);\n" %
                         self.cname)

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

        utils.print_docstring(self, pyfile, indent + 4)


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
        for scope in self.subscopes:
            scope.print_pycode(pyfile, indent + 4)

    def print_finalize_pycode(self, pyfile):
        pyfile.write("wrapper_lib.eval_class_attrs(%s)\n" % self.unscopedpyname)

        # XXX Should this be a decorator or maybe part of the metaclass?
        #     Should the unscopedname be used? Maybe this should be user
        #     configurable?
        pyfile.write("wrapper_lib.register_cpp_classname('%s', %s)\n" %
                         (self.name, self.unscopedpyname))

        for type in self.types:
            type.print_finalize_pycode(pyfile)

    def print_headercode(self, hfile):
        for inc in self.included_headers:
            hfile.write("#include <%s>\n" % inc)
        if not self.hassubclass or self.uninstantiable:
            return

        hfile.write(nci("""\
        class {0.cppname} : public {0.unscopedname}
        {{
        public:""".format(self)))

        for obj in self.objects:
            obj.print_headercode(hfile)

        # TODO: Do I want to always write the flag here or do I pull it in
        #       using a template super-class?

        hfile.write("    signed char vflags[%d];\n" % len(self.virtualmethods))

        hfile.write("};\n\n")

    def print_nested_headercode(self, hfile):
        # XXX Making a non-future proof assumption: no objects nested inside
        #     a wrapped class have their own header code to print, except for
        #     other wrapped classes.
        for type in self.types:
            type.print_headercode(hfile)

    def print_cppcode(self, cppfile):
        if len(self.virtualmethods) > 0 and not self.uninstantiable:
            cppfile.write(nci("""\
            WL_C_INTERNAL void(*{0.cname}_vtable[{1}])();

            WL_C_INTERNAL void {0.cname}_set_flag({0.cppname} *self, int i)
            {{
                self->vflags[i] = 1;
            }}

            WL_C_INTERNAL void {0.cname}_set_flags({0.cppname} *self, char *flags)
            {{
                memcpy(self->vflags, flags, sizeof(self->vflags));
            }}""".format(self, len(self.virtualmethods))))

        if self.convert_subclass_code is not None:
            cppfile.write(nci("""\
            WL_C_INTERNAL const char * cffigetclassname_{0.cname}({0.cppname} *cpp_obj)
            {{""".format(self)))
            cppfile.write(nci(self.convert_subclass_code, 4))
            cppfile.write("}\n")

    def call_cdef_param_setup(self, typeinfo, name):
        if typeinfo.flags.out:
            return ("{0}{1.OUT_PARAM_SUFFIX} = ffi.new('{1.cdef_type}')"
                     .format(name, typeinfo))

        conversion = ''
        if self.convert_pyobj_code is not None:
            conversion = "{0} = {1}._pyobject_mapping_.convert({0})".format(
                name, self.unscopedpyname)

        if typeinfo.flags.inout:
            return conversion + """\
            {0} = wrapper_lib.get_ptr({0})
            {0}{1.OUT_PARAM_SUFFIX} = ffi.new('{1.cdef_type}', {0})
            """.format(name, typeinfo)

        if typeinfo.flags.array:
            return ("{0}, {1.ARRAY_SIZE_PARAM}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2}).to_c({0})"
                    .format(name, typeinfo, self.unscopedpyname))
        return conversion if conversion != '' else None

    def call_cdef_param_inline(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return name + typeinfo.OUT_PARAM_SUFFIX
        if typeinfo.flags.array:
            return name
        return 'wrapper_lib.get_ptr(%s)' % name

    def call_cpp_param_setup(self, typeinfo, name):
        if (typeinfo.flags.out and typeinfo.ptrcount != 2 and
            not (typeinfo.ptrcount == 1 and typeinfo.refcount)):
            # Allocate a new object for `*` or `&` out parameters. Do not
            # create a new object for `**` or `&*` parameters.
            return "*{0} = new {1};".format(name, self.cppname)
        if typeinfo.flags.array:
            return "{0} {1}_converted = {2}({1}, {3});".format(
                typeinfo.c_virt_return_type, name, self.to_cpp_array_name,
                typeinfo.ARRAY_SIZE_PARAM)
        return None

    def call_cpp_param_inline(self, typeinfo, name):
        if typeinfo.flags.array:
            return name + "_converted"
        if typeinfo.flags.out or typeinfo.flags.inout:
            if typeinfo.refcount:
                return '*' * (2 - typeinfo.ptrcount) + name
            elif typeinfo.ptrcount == 1:
                return '*' + name
            else:
                return name
        deref = not typeinfo.ptrcount
        return ('*' if deref else '') + name

    def call_cpp_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.array and not typeinfo.flags.transfer:
            return 'delete[] %s_converted;' % name
        return None

    def virt_py_param_setup(self, typeinfo, name):
        if typeinfo.flags.inout:
            return ('{0}_tmpobj = wrapper_lib.obj_from_ptr({0}[0], {1})'
                    .format(name, self.unscopedpyname))

        if typeinfo.flags.array:
            return ("{0}_tmpobj = wrapper_lib.create_array_type({2}).to_py({0}, {1})"
                    .format(name, typeinfo.ARRAY_SIZE_PARAM, self.unscopedpyname))

        takeownership = ''
        if (self.copy_ctor_visibility != 'private' and
            not self.uninstantiable) and (
             typeinfo.const and not typeinfo.flags.nocopy or
             not typeinfo.refcount and not typeinfo.ptrcount):
            takeownership = ', True'
        return ('{0}_tmpobj = wrapper_lib.obj_from_ptr({0}, {1}{2})'
                .format(name, self.unscopedpyname, takeownership))

    def virt_py_param_inline(self, typeinfo, name):
        if typeinfo.flags.array:
            return ("wrapper_lib.create_array_type({2}).to_py({0}, {1})"
                    .format(name, typeinfo.ARRAY_SIZE_PARAM, self.unscopedpyname))
        return name + '_tmpobj'

    def virt_py_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return ("{0}[0] = wrapper_lib.get_ptr({0}{1.PY_RETURN_SUFFIX})"
                    .format(name, typeinfo))

    def virt_py_return(self, typeinfo, name):
        # Replicate sip's (largely undocumented) handling of ownership of
        # objects returned by virtual methods annotated with factory or
        # transfer_back:
        return ("""\
        wrapper_lib.give_ownership({0}, None, {1})
        {0} = wrapper_lib.get_ptr({0})"""
        .format(name, typeinfo.flags.factory or typeinfo.flags.transfer_back))

    def virt_cpp_param_setup(self, typeinfo, name):
        if typeinfo.flags.array:
            return None

        if typeinfo.ptrcount == 2 or (typeinfo.refcount and typeinfo.ptrcount):
            return None

        if typeinfo.flags.out or typeinfo.flags.inout:
            if typeinfo.ptrcount:
                init = name
            else: # typeinfo.refcount
                init = '&' + name
            return "%s %s_ptr = %s;" % (typeinfo.c_virt_return_type, name, init)

    def virt_cpp_param_inline(self, typeinfo, name):
        if typeinfo.flags.array:
            return "%s(%s, %s)" % (self.to_c_array_name, name,
                                   typeinfo.ARRAY_SIZE_PARAM)
        if typeinfo.flags.out or typeinfo.flags.inout:
            if typeinfo.ptrcount == 2:
                return name
            elif typeinfo.refcount and typeinfo.ptrcount:
                return '&' + name
            else:
                return '&' + name + "_ptr"

        # Always pass wrapped classes as pointers. If this is by value or
        # a const reference, it needs to be copy constructored onto the
        # heap, with Python taking ownership of the new object.
        if typeinfo.ptrcount:
            return name
        elif typeinfo.refcount and (not typeinfo.const or typeinfo.flags.nocopy or
                             not self.uninstantiable):# or
            return '&' + name
        else:
            return "new %s(%s)" % (self.cppname, name)


    def virt_cpp_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            if typeinfo.ptrcount != 2 and not (typeinfo.refcount and
                                               typeinfo.ptrcount):
                deref = '*' if typeinfo.ptrcount else ''
                return """\
                if({1}_ptr != NULL)
                    {0}{1} = *{1}_ptr;""".format(deref, name)

    def virt_cpp_return(self, typeinfo, name):
        return ('*' if not typeinfo.ptrcount else '') + name

    def convert_variable_cpp_to_c(self, typeinfo, name):
        # Always pass wrapped classes as pointers. If this is by value or
        # a const reference, it needs to be copy constructored onto the
        # heap, with Python taking ownership of the new object.
        if (self.copy_ctor_visibility != 'private' and
            not self.uninstantiable) and (
             typeinfo.const and not typeinfo.flags.nocopy or
             not typeinfo.refcount and not typeinfo.ptrcount):
            # If returning a const object (and nocopy isn't set) make a copy of
            # the object (that Python will own) so it can be modified safely
            deref = '*' if typeinfo.ptrcount else ''
            return "new %s(%s%s)" % (self.cppname, deref, name)
        else:
            ref = '&' if not typeinfo.ptrcount else ''
            return ref + name

    def convert_variable_c_to_py(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return 'wrapper_lib.obj_from_ptr(%s%s[0], %s)' % (
                    name, typeinfo.OUT_PARAM_SUFFIX, self.unscopedpyname)
        if (self.copy_ctor_visibility != 'private' and
            not self.uninstantiable) and (
             typeinfo.const and not typeinfo.flags.nocopy or
             not typeinfo.refcount and not typeinfo.ptrcount):
            return 'wrapper_lib.obj_from_ptr(%s, %s, True)' % (
                    name, self.unscopedpyname)
        return 'wrapper_lib.obj_from_ptr(%s, %s)' % (
                name, self.unscopedpyname)

    def user_cpp_param_inline(self, typeinfo, name):
        # Wrapped types are always handled as pointers. The various annotations
        # don't affect this.
        if typeinfo.ptrcount == 2:
            return '*(' + name + ')'
        if typeinfo.ptrcount == 1:
            return name
        return '&(' + name + ')'

    def user_cpp_return(self, typeinfo, name):
        # The user's C++ code should return a pointer, so deref as needed.
        if typeinfo.ptrcount:
            return name
        return '*(' + name + ')'
