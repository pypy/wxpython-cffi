from .base import (
    utils, nci, args_string, FunctionBase, Param, SelfParam, VoidType, TypeInfo)

# Originally copied from tweaker_tools:
CPP_OPERATORS = {
    'operator!='    : '__ne__',
    'operator=='    : '__eq__',
    'operator<'     : '__lt__',
    'operator<='    : '__le__',
    'operator>'     : '__gt__',
    'operator>='    : '__ge__',
    'operator+'     : '__add__',
    'operator-'     : '__sub__',
    'operator*'     : '__mul__',
    'operator/'     : '__div__',
    'operator+='    : '__iadd__',
    'operator-='    : '__isub__',
    'operator*='    : '__imul__',
    'operator/='    : '__idiv__',
    'operator bool' : '__int__',  # Why not __nonzero__?
    'operator()'   : '__call__',
}


class Method(FunctionBase):
    PREFIX = 'wrappedmeth_'

    def __init__(self, meth, parent):
        super(Method, self).__init__(meth, parent)

        # Methods of a deprecated class are also deprecated
        if parent.flags.deprecated:
           self.flags.deprecated = True

        self.virtual = meth.isVirtual
        self.purevirtual = meth.isPureVirtual
        self.const = meth.isConst
        self.protection = meth.protection

        if self.name in CPP_OPERATORS:
            self.pyname = CPP_OPERATORS[self.name]
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

    @utils.call_once
    def setup(self):
        super(Method, self).setup()
        self.params = [SelfParam(self)] + self.params

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
            return code + ('{0.WRAPPER_PREFIX}{0.cname}{0.call_cpp_args};\n'
                           .format(self))

        if self.protection != 'protected':
            code += 'self->'
        else:
            # Cast to the generated subclass for protected methods
            code += '(({0.parent.cppname}*)self)->unprotected_'.format(self)
        return code + '{0.name}{0.call_cpp_args};\n'.format(self)

    def print_cppcode(self, cppfile):
        super(Method, self).print_cppcode(cppfile)

        if self.virtual:
            self.print_virtual_cppcode(cppfile)

    def print_headercode(self, hfile):
        if self.virtual:
            hfile.write("    virtual {0.type.original} {0.name}{0.cpp_args}{1};\n"
                        .format(self, ' const' if self.const else ''))

        if self.protection == 'protected':
            ret_stmt = "return " if not isinstance(self.type.type, VoidType) else ''
            const_stmt = ' const' if self.const else ''
            hfile.write(nci("""\
            {0.type.cpp_type} unprotected_{0.name}{0.cpp_args}{1}
            {{
                {2}this->{0.parent.unscopedname}::{0.name}{0.call_original_cpp_args};
            }}""".format(self, const_stmt, ret_stmt), 4))

    def print_virtual_cppcode(self, cppfile):
        # Create a typedef that will be used to cast the pointer from the
        # vtable. A typedef is necessary because it is the only way to cast a
        # function pointer to be `extern "C"`.
        cppfile.write(nci("""\
        extern "C" typedef {0.type.c_virt_return_type} (*{0.cname}_funcptr){0.c_virt_args};
        {0.type.cpp_type} {0.parent.cppname}::{0.name}{0.cpp_args}
        {{""".format(self)))

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

        cppfile.write(' ' * 8)
        if not isinstance(self.type.type, VoidType):
            cppfile.write('{0.type.c_virt_return_type} cppreturnval = '.format(self))
        cppfile.write('(({0.cname}_funcptr){0.parent.cname}_vtable[{0.vtable_index}]){0.call_virtual_cpp_args};\n'.format(self))

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
        if self.virtual:
            self.print_virtual_pycode(pyfile, indent)
            pyfile.write(nci("@wrapper_lib.VirtualMethod(%d)" % self.vtable_index,
                            indent))
        if not self.purevirtual:
            super(Method, self).print_pycode(pyfile, indent)
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

    def can_override(self, other):
        # Don't bother checking the return types. Its a compiler error if the
        # parameters and names match but the return types don't.
        if ((self.name != other.name) or
            (len(self.params) != len(other.params)) or
            (self.virtual is not other.virtual) or
            (self.const is not other.const)):
            return False
        return all(p == other.params[i] for i, p in enumerate(self.params))


class InheritedVirtualMethod(Method):
    """
    A virtual method which is inherited from a base class. This tries to reuse
    as much code from the original as possible.
    """
    def __init__(self, parent, vmeth):
        super(InheritedVirtualMethod, self).__init__(vmeth.item, parent)
        self.setup()

        self.original = vmeth

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("""\
        {0.pyname} = wrapper_lib.VirtualMethodStub({0.original.unscopedpyname}, {0.vtable_index})
        _virtual__{0.vtable_index} = wrapper_lib.VirtualDispatcher({0.vtable_index})({0.original.parent.pyname}._vdata.vtable[{0.original.vtable_index}])
        """.format(self), indent))

    def print_cppcode(self, cppfile):
        self.print_virtual_cppcode(cppfile)

    def print_cdef_and_verify(self, pyfile):
        pass
