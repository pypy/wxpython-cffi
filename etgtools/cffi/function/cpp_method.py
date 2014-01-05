from .function import Function
from .method import nci, Param, SelfParam, Method, args_string, InheritedVirtualMethodMixin
from .ctor import CtorMethod
from ..basictype import VoidType

from ..base import CppType

from ... import extractors

def cpp_method(cls):
    def extract_params(self):
        """
        CppMethodDefs are always specified with an empty parameter list. So
        that they may be treated like regular FunctionDefs where ever possible,
        this method will disassemble their args string into a list of Params.
        """
        for p in extractors.ArgsString(self.func.argsString):
            param = Param(p, self)
            self.params.append(param)
    cls.extract_params = extract_params

    def __init__(self, meth, parent):
        original__init__(self, meth, parent)
        self.cppcode = meth.body
        self.extract_params()
    original__init__ = cls.__init__
    cls.__init__ = __init__

    return cls

@cpp_method
class GlobalCppMethod(Function):
    pass

@cpp_method
class MemberCppMethod(Method):
    def copy_onto_subclass(self, cls):
        # It doesn't really make sense to have a MemberCppMethod be virtual;
        # there is no way for a user to override the method from Python and be
        # able to expect it to behave correctly.
        raise NotImplementedError()

@cpp_method
class CppCtorMethod(CtorMethod):
    pass



# TODO: Implement GlobalCppMethod_cffi?

class MemberCppMethod_cffi(Method):
    @args_string
    def py_args(self):
        for p in self.py_params:
            if p.default:
                yield '%s=%s' % (p.name, p.default)
            else:
                yield p.name

    @args_string
    def py_types_args(self):
        for p in self.py_params:
            if p.type.original == 'WL_Self':
                # This should be treated like a SelfParam, which is to say,
                # it does not need to be typechecked.
                continue
            type = p.type.py_type if p.type.original != 'WL_Object' else 'object'

            if self.overload_manager.is_overloaded():
                yield "%s='%s'" % (p.name, type)
            else:
                yield '("{0}", {1}, {0})'.format(p.name, type)

    def __init__(self, meth, parent):
        self.user_py_args_list = meth.pyArgs
        self.user_py_code = meth.pyBody

        self.user_c_args = meth.cArgsString
        self.user_c_code = meth.cBody

        if self.user_c_code:
            # Don't try handling the type when we have custom C++ code. The
            # user can specify any type in this situation.
            self.user_c_type = meth.cReturnType

        super(MemberCppMethod_cffi, self).__init__(meth, parent)

        if meth.virtualPyArgs is not None:
            self.c_virt_args = meth.virtualCArgsString
            self.cdef_virt_args = self.c_virt_args

            self.cpp_code = meth.virtualCBody

            self.py_virt_args = meth.virtualPyArgs
            self.py_code = meth.virtualPyBody

        if meth.originalCppArgs is not None:
            self.call_original_cpp_args = ('(' +
                ', '.join([i.name for i in meth.originalCppArgs]) + ')')
            self.params += [Param(i, self) for i in self.item.originalCppArgs]

        self.py_params = [Param(i, self) for i in self.user_py_args_list]

    def setup(self):
        super(MemberCppMethod_cffi, self).setup()

        for p in self.py_params:
            p.setup()

        if self.item.originalCppType is not None:
            self.type = FakeTypeInfo(self.item.originalCppType,
                                     self.item.virtualCReturnType)


    def print_pycode(self, pyfile, indent=0):
        if not self.user_py_code:
            super(MemberCppMethod_cffi, self).print_pycode(pyfile, indent)
            return

        if self.virtual:
            pyfile.write(nci("""\
            @wrapper_lib.VirtualDispatcher({0.vtable_index})
            @ffi.callback('{0.type.cdef_virt_return_type}(*){0.cdef_virt_args}')
            def _virtual__{0.vtable_index}{0.py_virt_args}:
            """.format(self), indent))
            pyfile.write(nci(self.py_code, indent + 4))

            pyfile.write(nci("@wrapper_lib.VirtualMethod(%d)" % self.vtable_index,
                            indent))

        self.print_pycode_header(pyfile, indent)
        pyfile.write(nci("call = clib." + self.cname, indent + 4))
        pyfile.write(nci(self.user_py_code, indent + 4))


    def print_cdef_and_verify(self, pyfile):
        if self.user_c_code is None:
            pyfile.write("void {0.cname}();\n".format(self))
            return

        pyfile.write("{0.user_c_type} {0.cname}{0.user_c_args};\n".format(self))

    def print_headercode(self, hfile):
        if self.virtual:
            hfile.write("    virtual {0.type.original} {0.name}{0.cpp_args}{1};\n"
                        .format(self, ' const' if self.const else ''))

    def print_cppcode(self, cppfile):
        if self.user_c_code is None:
            cppfile.write("WL_C_INTERNAL void {0.cname}() {{ }}\n".format(self))
            return

        cppfile.write(nci("""\
        #define WL_CLASS_NAME {0.parent.cppname}
        WL_C_INTERNAL {0.user_c_type} {0.cname}{0.user_c_args}
        {{""".format(self)))
        cppfile.write(nci(self.user_c_code, 4))
        cppfile.write(nci("""\
        }
        #undef WL_CLASS_NAME"""))

        if self.virtual and not self.parent.uninstantiable:
            self.print_virtual_cppcode(cppfile)

    def print_virtual_cppcode_body(self, cppfile):
        cppfile.write(nci("{0.cname}_funcptr call = ({0.cname}_funcptr){0.parent.cname}_vtable[{0.vtable_index}];\n"
                      .format(self), 8))
        cppfile.write(nci(self.cpp_code, 8))

    def copy_onto_subclass(self, cls):
        InheritedVirtualCppMethod_cffi(self, cls)

class CppCtorMethod_cffi(MemberCppMethod_cffi, CtorMethod):
    def print_headercode(self, hfile):
        hfile.write('    {0.parent.cppname}{0.cpp_args} : {0.parent.unscopedname}{0.call_original_cpp_args} {{ }}\n'.format(self))

class FakeTypeInfo(object):
    """
    A fake TypeInfo for CppMethod_cffi's which have a custom virtual return
    type. It fakes the necessary fields so the method prints correctly.
    """
    def __init__(self, c_type, cpp_type):
        self.original = cpp_type
        self.cpp_type = self.original

        self.c_virt_return_type = c_type
        self.cdef_virt_return_type = self.c_virt_return_type

        if self.original == 'void':
            self.type = VoidType()
        else:
            self.type = None

class InheritedVirtualCppMethod_cffi(InheritedVirtualMethodMixin, MemberCppMethod_cffi):
    pass
