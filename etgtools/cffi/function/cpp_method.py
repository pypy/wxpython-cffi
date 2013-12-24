from .function import Function
from .method import nci, Param, SelfParam, Method, args_string
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
        Based heavily on extractors.FunctionDef.makePyArgsString
        """
        params = []
        args = self.func.argsString.rsplit(')')[0].strip('(').split(',')
        for arg in args:
            if not arg:
                continue
            param = extractors.ParamDef()
            # Is there a default value?
            if '=' in arg:
                param.default = arg.split('=')[1].strip()
                arg = arg.split('=')[0].strip()
            # Now the last word should be the variable name, and everything
            # before it is the type
            param.type, param.name = arg.rsplit(' ', 1)
            self.params.append(Param(param, self.parent))
            self.params[-1].setup()
    cls.extract_params = extract_params

    def __init__(self, meth, parent):
        original__init__(self, meth, parent)
        self.cppcode = meth.body
    original__init__ = cls.__init__
    cls.__init__ = __init__

    def setup(self):
        original_setup(self)
        self.extract_params()
    original_setup = cls.setup
    cls.setup = setup

    return cls

@cpp_method
class GlobalCppMethod(Function):
    pass

@cpp_method
class MemberCppMethod(Method):
    pass

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
            type = p.type.py_type if p.type.original != 'WL_Object' else 'object'

            if self.overload_manager.is_overloaded():
                yield "%s='%s'" % (p.name, type)
            else:
                yield '("{0}", {1}, {0})'.format(p.name, type)

    def __init__(self, meth, parent):
        if meth.isCtor:
            meth.pyName = '__init__'
            meth.type = parent.unscopedname + '*'

        self.user_py_args_list = meth.pyArgs
        self.user_py_code = meth.pyBody

        self.user_c_args = meth.cArgsString
        self.user_c_code = meth.cBody

        if self.user_c_code:
            # Don't try handling the type when we have custom C++ code. The
            # user can specify any type in this situation.
            self.user_c_type = meth.cReturnType
            meth.type = 'void'

        super(MemberCppMethod_cffi, self).__init__(meth, parent)

        self.virtual_handler = meth.virtualHandler
        if self.virtual_handler is not None:
            self.c_virt_args = self.virtual_handler.funcPtrArgsString
            self.cdef_virt_args = self.c_virt_args

            self.cpp_code = self.virtual_handler.cBody

            self.py_virt_args = self.virtual_handler.pyArgs
            self.py_code = self.virtual_handler.pyBody

            if self.virtual_handler.originalCppType is not None:
                self.cpp_type = self.virtual_handler.originalCppType

            if self.virtual_handler.originalCppArgs is not None:
                self.call_original_cpp_args = ('(' +
                    ', '.join([i.name for i in self.virtual_handler.originalCppArgs]) + ')')

    def setup(self):
        super(MemberCppMethod_cffi, self).setup()

        self.py_params = [Param(i, self.parent) for i in self.user_py_args_list]
        for p in self.py_params:
            p.setup()

        if self.virtual_handler is not None:
            self.params = [Param(i, self.parent)
                           for i in self.virtual_handler.originalCppArgs]
            for p in self.params:
                p.setup()

            assert self.virtual_handler.originalCppType is not None
            self.type = FakeTypeInfo(self.virtual_handler)


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
        WL_C_INTERNAL {0.user_c_type} {0.cname}{0.user_c_args}
        {{""".format(self)))
        cppfile.write(nci(self.user_c_code))
        cppfile.write("}\n")

        if self.virtual:
            self.print_virtual_cppcode(cppfile)

    def print_virtual_cppcode_body(self, cppfile):
        cppfile.write(nci("{0.cname}_funcptr call = ({0.cname}_funcptr){0.parent.cname}_vtable[{0.vtable_index}];\n"
                      .format(self), 8))
        cppfile.write(nci(self.cpp_code, 8))

class FakeTypeInfo(object):
    """
    A fake TypeInfo for CppMethod_cffi's which have a custom virtual return
    type. It fakes the necessary fields so the method prints correctly.
    """
    def __init__(self, virtual_handler):
        self.original = virtual_handler.originalCppType
        self.cpp_type = self.original

        self.c_virt_return_type = virtual_handler.funcPtrReturnType
        self.cdef_virt_return_type = self.c_virt_return_type

        if virtual_handler.originalCppType.strip() == 'void':
            self.type = VoidType()
        else:
            self.type = None
