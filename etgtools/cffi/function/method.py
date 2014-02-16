from .base import (
    utils, nci, args_string, FunctionBase, Param, SelfParam, VoidType,
    TypeInfo, OverloadManager)
from .operators import get_operator


class MethodOverloadManager(OverloadManager):
    @utils.call_once
    def print_pycode(self, pyfile, indent):
        indices = [str(f.vtable_index) for f in self.functions if f.virtual]
        if len(indices) > 0:
            pyfile.write(nci("@wrapper_lib.VirtualMethod(%s)" %
                             ', '.join(indices), indent))

        super(MethodOverloadManager, self).print_pycode(pyfile, indent)

class Method(FunctionBase):
    PREFIX = 'wrappedmeth_'
    OVERLOAD_MANAGER = MethodOverloadManager

    def __init__(self, meth, parent):
        super(Method, self).__init__(meth, parent)

        # Methods of a deprecated class are also deprecated
        if parent.flags.deprecated:
           self.flags.deprecated = True

        self.virtual = meth.isVirtual
        self.purevirtual = meth.isPureVirtual
        self.const = meth.isConst
        self.protection = meth.protection

        self.params = [SelfParam(self)] + self.params

        self.operator = get_operator(self)
        if self.operator is not None:
            self.pyname = self.operator.pyname
            self.cname = self.cname[:-len(self.name)] + self.pyname

        if self.protection == 'protected':
            self.parent.protectedmethods.append(self)
        if self.virtual:
            self.vtable_index = len(self.parent.virtualmethods)
            self.parent.virtualmethods.append(self)

        if not self.flags.factory:
            # Non-factory methods transfer ownership to the method's instance
            self.ownership_transfer_name = "self"
            self.keepref_on_object = True

    @args_string
    def call_virtual_cpp_args(self):
        for param in self.params:
            if isinstance(param, SelfParam):
                yield 'this'
                continue
            yield param.type.virt_cpp_param_inline(param.name)

    @args_string
    def call_virtual_py_args(self):
        for param in self.params:
            if (isinstance(param, SelfParam) or param.flags.arraysize or
                param.flags.out):
                continue
            yield param.type.virt_py_param_inline(param.name)

    @args_string
    def c_virt_args(self):
        for param in self.params:
            yield param.type.c_virt_type

    @args_string
    def cdef_virt_args(self):
        for param in self.params:
            yield param.type.cdef_virt_type

    @args_string
    def py_virt_args(self):
        # This differs from py_args because py_args doesn't include, e.g.
        # arraysize arguments.
        for param in self.params:
            yield param.name

    @property
    def call_cpp_code(self):
        code = ''
        if not isinstance(self.type.type, VoidType):
            code = '{0.type.cpp_type} cppreturnval = '.format(self)

        if self.cppcode:
            # If we have custom C++ code, call the wrapper for it
            return code + ('{0.wrapper_call_code};\n'.format(self))

        if self.operator is not None:
            return (code + self.operator.cpp_code(
                            '(*self)', *type(self).call_cpp_args(self)) + ';')

        if self.protection != 'protected':
            code += 'self->'
            if self.virtual and not self.purevirtual:
                code +=  self.parent.unscopedname + '::'
        else:
            # Cast to the generated subclass for protected methods
            code += '(({0.parent.cppname}*)self)->unprotected_'.format(self)
        return code + '{0.name}{0.call_cpp_args};\n'.format(self)

    @property
    def deprecated_msg(self):
        return "%s.%s() is deprecated" % (self.parent.name, self.name)

    def print_cppcode(self, cppfile):
        if self.protection == 'private':
            return
        super(Method, self).print_cppcode(cppfile)

        if self.virtual and not self.parent.uninstantiable:
            self.print_virtual_cppcode(cppfile)

    def print_headercode(self, hfile):
        if self.protection == 'private':
            return

        if self.virtual:
            hfile.write("    virtual {0.type.original} {0.name}{0.cpp_args}{1};\n"
                        .format(self, ' const' if self.const else ''))

        if self.protection == 'protected':
            ret_stmt = "return " if not isinstance(self.type.type, VoidType) else ''
            const_stmt = ' const' if self.const else ''
            scoping =  '' if self.purevirtual else (self.parent.unscopedname + '::')
            hfile.write(nci("""\
            {0.type.cpp_type} unprotected_{0.name}{0.cpp_args}{1}
            {{
                {2}this->{3}{0.name}{0.call_original_cpp_args};
            }}""".format(self, const_stmt, ret_stmt, scoping), 4))

    def print_virtual_cppcode(self, cppfile):
        # Create a typedef that will be used to cast the pointer from the
        # vtable. A typedef is necessary because it is the only way to cast a
        # function pointer to be `extern "C"`.
        const_stmt = ' const' if self.const else ''
        cppfile.write(nci("""\
        extern "C" typedef {0.type.c_virt_return_type} (*{0.cname}_funcptr){0.c_virt_args};
        {0.type.cpp_type} {0.parent.cppname}::{0.name}{0.cpp_args}{1}
        {{""".format(self, const_stmt)))

        if not self.purevirtual:
            returns = not isinstance(self.type.type, VoidType)
            cppfile.write(nci("""\
            if(!this->vflags[{0.vtable_index}])
            {{
                {1}this->{0.parent.unscopedname}::{0.name}{0.call_original_cpp_args};
            }}
            else""".format(self, 'return ' if returns else ''), 4))
        cppfile.write("    {\n")

        self.print_virtual_cppcode_body(cppfile)

        cppfile.write("    }\n}\n\n")

    def print_virtual_cppcode_body(self, cppfile):
        """
        Subclasses can override this method to print custom code to be run when
        a user-overridden virtual method is called.
        """
        for param in self.params:
            conversion = param.type.virt_cpp_param_setup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 8))

        # This is a workaround for a bug present in clang through at least 3.3
        cppfile.write(nci("""\
        {0.cname}_funcptr python_virtual_handler =
            ({0.cname}_funcptr){0.parent.cname}_vtable[{0.vtable_index}];
        """.format(self), 8))

        cppfile.write(' ' * 8)
        if not isinstance(self.type.type, VoidType):
            cppfile.write('{0.type.c_virt_return_type} cppreturnval = '.format(self))
        cppfile.write('python_virtual_handler{0.call_virtual_cpp_args};\n'
                      .format(self))

        for param in self.params:
            conversion = param.type.virt_cpp_param_cleanup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 8))

        if not isinstance(self.type.type, VoidType):
            cppfile.write(nci('return %s;' % self.type.virt_cpp_return('cppreturnval'),
                              8))

    def print_pycode_ownership_transfer(self, pyfile, indent):
        super(Method, self).print_pycode_ownership_transfer(pyfile, indent)

        # Some transfer types that can only be applied to methods:
        if self.flags.transfer:
            if self.return_has_external_ref:
                pyfile.write(nci("wrapper_lib.give_ownership(self, "
                                 "external_ref=True)", indent + 4))
            else:
                pyfile.write(nci(
                    "wrapper_lib.give_ownership(creturnval, self)",
                    indent + 4))
        if self.flags.transfer_this:
            pyfile.write(nci("wrapper_lib.give_ownership(self)", indent + 4))

    def print_pycode(self, pyfile, indent):
        if self.protection != 'private':
            super(Method, self).print_pycode(pyfile, indent)

        if self.virtual and self.protection != 'private':
            self.print_virtual_pycode(pyfile, indent)

    def print_actual_pycode(self, pyfile, indent):
        if self.protection == 'private':
            super(Method, self).print_pycode_header(pyfile, indent)
            pyfile.write(nci(
                "raise NotImplementedError('%s.%s() is a private method')"
                % (self.parent.pyname, self.pyname), indent + 4))
        elif not self.purevirtual:
            super(Method, self).print_actual_pycode(pyfile, indent)
        else:
            super(Method, self).print_pycode_header(pyfile, indent)
            pyfile.write(nci(
                "raise NotImplementedError('%s.%s() is abstract and must be "
                "overridden')" % (self.parent.pyname, self.pyname), indent + 4))

    def print_virtual_pycode(self, pyfile, indent):
        pyfile.write(nci("""\
        @wrapper_lib.VirtualDispatcher({0.vtable_index})
        @ffi.callback('{0.type.cdef_virt_return_type}(*){0.cdef_virt_args}')
        def _virtual__{0.vtable_index}{0.py_virt_args}:
        """.format(self), indent))

        outvars = []
        for param in self.params:
            if param.flags.out or param.flags.inout:
                outvars.append(param.name + TypeInfo.PY_RETURN_SUFFIX)
            conversion = param.type.virt_py_param_setup(param.name)
            if conversion is not None:
                pyfile.write(nci(conversion, indent + 4))

        # Print the call to the Python implementation
        pyfile.write(' ' * (indent + 4))
        # Note, no assigment will be printed if there's not return value
        if len(outvars) > 1 or not isinstance(self.type.type, VoidType):
            pyfile.write('pyreturnval = ')
        elif len(outvars) == 1:
            pyfile.write('%s = ' % outvars[0])

        pyfile.write('{1}.{0.pyname}{0.call_virtual_py_args}\n'
                    .format(self, self.params[0].type.virt_py_param_inline('self')))

        # If there were multiple return values, unpack them
        if len(outvars) > 1 or (not isinstance(self.type.type, VoidType) and
                                len(outvars) > 0):
            if not isinstance(self.type.type, VoidType):
                outvars = ['pyreturnval'] + outvars
            pyfile.write(nci("""\
            try:
                %s = pyreturnval
            except ValueError:
                raise
            """ % ', '.join(outvars), indent + 4))

        for param in self.params:
            conversion = param.type.virt_py_param_cleanup(param.name)
            if conversion is not None:
                pyfile.write(nci(conversion, indent + 4))

        if not isinstance(self.type.type, VoidType):
            conversion = self.type.virt_py_return('pyreturnval')
            if conversion is not None:
                pyfile.write(nci(conversion, indent + 4))
            pyfile.write(nci('return pyreturnval', indent + 4))

    def print_cdef_and_verify(self, pyfile):
        if self.protection == 'private':
            return

        super(Method, self).print_cdef_and_verify(pyfile)

    def can_override(self, other):
        # Don't bother checking the return types. Its a compiler error if the
        # parameters and names match but the return types don't.
        if ((self.name != other.name) or
            (len(self.params) != len(other.params)) or
            (self.virtual is not other.virtual) or
            (self.const is not other.const)):
            return False
        return all(p == other.params[i] for i, p in enumerate(self.params))

    def copy_onto_subclass(self, cls):
        InheritedVirtualMethod(self, cls)

class InheritedVirtualMethodMixin(object):
    @args_string
    def vtable_indices(self):
        for m in self.overload_manager.functions:
            yield str(m.vtable_index)

    def __init__(self, original_method, new_class):
        self.__dict__.update(original_method.__dict__)
        self.parent = new_class
        self.overload_manager = MethodOverloadManager(self)
        self.original = original_method

        if self.protection == 'protected':
            self.parent.protectedmethods.append(self)

        self.vtable_index = len(self.parent.virtualmethods)
        self.parent.virtualmethods.append(self)

        self.parent.objects.append(self)

        # Check if this is the first overload being copied into the new class.
        # Reaching here means that there are no methods in the the class with
        # the same name in the new class anyway
        self.first_overload = not self.overload_manager.is_overloaded()

    def print_pycode(self, pyfile, indent=4):
        if self.first_overload:
            # Coping calling code from the base class
            indices = self.vtable_indices[1:-1]
            pyfile.write(nci("""\
            {0.pyname} = wrapper_lib.VirtualMethodStub({0.original.unscopedpyname}, {1})
            """.format(self, indices), indent))

        pyfile.write(nci("""\
        _virtual__{0.vtable_index} = wrapper_lib.VirtualDispatcher({0.vtable_index})({0.original.parent.pyname}._vdata.vtable[{0.original.vtable_index}])
        """.format(self), indent))

    def print_cdef_and_verify(self, pyfile):
        pass

    def print_cppcode(self, cppfile):
        if self.protection == 'private':
            return

        if not self.parent.uninstantiable:
            self.print_virtual_cppcode(cppfile)

class InheritedVirtualMethod(InheritedVirtualMethodMixin, Method):
    pass
