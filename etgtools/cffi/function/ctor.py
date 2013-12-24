from .base import args_string, void_args_string
from .method import utils, nci, Method, Param, SelfParam
from ..wrappedtype import WrappedType

class CtorMethod(Method):
    def __init__(self, meth, parent):
        super(CtorMethod, self).__init__(meth, parent)
        self.pyname = '__init__'
        self.cname = self.cname[:-len(self.name)] + self.pyname
        self.item.type = self.parent.unscopedname + '*'

        # A ctor annotated wtih transfer will create an object with an extra
        # reference to prevent it's Python object from being deleted until the
        # C++ object is deleted.
        self.return_has_external_ref = True

    @args_string
    def c_args(self):
        if self.has_default_args():
            yield 'int defaults_bitflags'
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            yield " ".join((param.type.c_type, param.name))

    @void_args_string
    def cdef_args(self):
        if self.has_default_args():
            yield 'int defaults_bitflags'
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            yield param.type.cdef_type

    @args_string
    def call_cdef_args(self):
        if self.has_default_args():
            yield 'defaults_bitflags'
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            yield param.type.call_cdef_param_inline(param.name)

    @args_string
    def call_cpp_args(self):
        default_count = 1
        for param in self.params:
            # Don't include self even with custom C++ code
            if isinstance(param, SelfParam):
                continue
            if param.default:
                yield 'defaults_bitflags & %d ? %s : %s' % (
                    default_count, param.default,
                    param.type.call_cpp_param_inline(param.name))
                default_count <<= 1
            else:
                yield param.type.call_cpp_param_inline(param.name)

    @args_string
    def wrapper_args(self):
        for param in self.params:
            if isinstance(param, SelfParam):
                continue
            if isinstance(param.type.type, WrappedType):
                type = param.type.cpp_type.replace('&', '*')
            else:
                type = param.type.cpp_type
            yield " ".join((type, param.name))


    def iscopyctor(self):
        # Note that self.params[0] is always a SelfParam
        return len(self.params) == 2 and self.params[1].type is self.parent

    def print_headercode(self, hfile):
        hfile.write('    {0.parent.cppname}{0.cpp_args} : {0.parent.unscopedname}{0.call_original_cpp_args} {{ }}\n'.format(self))

    def print_pycode_call(self, pyfile, indent):
        pyfile.write(nci("""\
        creturnval = clib.{0.cname}{0.call_cdef_args}
        wrapper_lib.CppWrapper.__init__(self, creturnval)
        """.format(self), indent + 4))

    def print_pycode_return(self, pyfile, indent):
        # Instead of returning, call CppWrapper's constructor
        pass

    @property
    def call_cpp_code(self):
        code = '{0.type.cpp_type} cppreturnval = '.format(self)
        if self.cppcode:
            # If we have custom C++ code, call the wrapper for it
            return (code + '{0.WRAPPER_PREFIX}{0.cname}{0.call_cpp_args};\n'
                           .format(self))
        return code + 'new {0.parent.cppname}{0.call_cpp_args};\n'.format(self)

    def print_cdef_and_verify(self, pyfile):
        if not self.parent.uninstantiable:
            super(CtorMethod, self).print_cdef_and_verify(pyfile)

    def print_pycode_return(self, pyfile, indent):
        pass

    def print_pycode(self, pyfile, indent=0):
        if not self.parent.uninstantiable:
            super(CtorMethod, self).print_pycode(pyfile, indent)

    def print_cppcode(self, cppfile):
        if not self.parent.uninstantiable:
            super(CtorMethod, self).print_cppcode(cppfile)
