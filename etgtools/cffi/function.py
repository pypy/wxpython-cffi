from .base import CppObject, ItemFlags, TypeInfo
from .basictype import VoidType

from .wrappedtype import WrappedType

from .utils import nci, print_docstring

from .. import extractors

class Param(object):
    def __init__(self, param, scope):
        self.name = param.name
        self.default = param.default
        self.flags = ItemFlags(param)

        self.type = TypeInfo(scope, param.type, self.flags)

class void_args_string(object):
    def __init__(self, func):
        self.builder = func

    def __get__(self, func, cls=None):
        args = list(self.builder(func))
        if len(args) == 0:
            return '(void)'
        else:
            return '(' + ', '.join(args) + ')'

class args_string(object):
    def __init__(self, func):
        self.builder = func

    def __get__(self, func, cls=None):
        return '(' + ', '.join(self.builder(func)) + ')'

class FunctionBase(CppObject):
    WRAPPER_PREFIX = 'usercppwrapper_'
    def __init__(self, func, parent):
        super(FunctionBase, self).__init__(func, parent)
        self.func = func
        self.cname = self.PREFIX + self.cname

        self.cppcode = getattr(func, 'cppCode', None)
        if self.cppcode is not None:
            self.cppcode = self.cppcode[0]

    def setup(self):
        self.params = [Param(p, self.parent) for p in self.item.items]
        self.type = TypeInfo(self.parent, self.item.type, self.flags)

    @args_string
    def c_args(self):
        for param in self.params:
            yield " ".join((param.type.c_type, param.name))

    @void_args_string
    def cdef_args(self):
        for param in self.params:
            yield " ".join((param.type.cdef_type, param.name))

    @args_string
    def py_args(self):
        for param in self.params:
            yield param.name

    @args_string
    def wrapper_args(self):
        for param in self.params:
            if isinstance(param.type.type, WrappedType):
                type = param.type.original.replace('&', '*')
            else:
                type = param.type.original
            yield " ".join((type, param.name))

    @args_string
    def call_cdef_args(self):
        for param in self.params:
            yield param.type.call_cdef_param_inline(param.name)

    @args_string
    def call_cpp_args(self):
        for param in self.params:
            yield param.type.call_cpp_param_inline(param.name)

    def print_cdef_and_verify(self, pyfile):
        pyfile.write("{0.type.cdef_type} {0.cname}{0.cdef_args};\n".format(self))

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("def {0.pyname}{0.py_args}:".format(self), indent))
        print_docstring(self, pyfile, indent + 4)

        for param in self.params:
            conversion = param.type.call_cdef_param_setup(param.name)
            if conversion is not None:
                pyfile.write(nci(conversion, 4))

        pyfile.write('    ');
        if not isinstance(self.type.type, VoidType):
            pyfile.write('creturnval = '.format(self))

        call = 'clib.{0.cname}{0.call_cdef_args}'.format(self)
        pyfile.write(self.type.convert_variable_c_to_py(call) + '\n')

        for param in self.params:
            conversion = param.type.call_cdef_param_cleanup(param.name)
            if conversion is not None:
                pyfile.write(nci(conversion, 4))

        # TODO: Perform ownership transfers / pack out-params into a tuple

        if not isinstance(self.type.type, VoidType):
            pyfile.write(nci('return creturnval', indent + 4))

    def print_cppcode(self, cppfile):
        if self.cppcode:
            self.print_wrapper(cppfile)

        cppfile.write(nci("""\
        WL_INTERNAL {0.type.cdef_type} {0.cname}{0.c_args}
        {{""".format(self)))

        for param in self.params:
            conversion = param.type.call_cpp_param_setup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 4))

        cppfile.write('    ');
        if not isinstance(self.type.type, VoidType):
            cppfile.write('{0.type.original} cppreturnval = '.format(self))

        if self.cppcode:
            cppfile.write('{0.WRAPPER_PREFIX}{0.cname}{0.call_cpp_args};\n'
                           .format(self))
        else:
            cppfile.write('{0.name}{0.call_cpp_args};\n'.format(self))

        for param in self.params:
            conversion = param.type.call_cpp_param_cleanup(param.name)
            if conversion is not None:
                cppfile.write(nci(conversion, 4))

        if not isinstance(self.type.type, VoidType):
            cppfile.write('    return %s;\n' %
                           self.type.convert_variable_cpp_to_c('cppreturnval'))

        cppfile.write('}\n\n')

    def print_wrapper(self, cppfile):
        cppfile.write(nci("""\
        WL_INTERNAL {0.type.original} {0.WRAPPER_PREFIX}{0.cname}{0.wrapper_args}
        {{""".format(self)))

        cppfile.write(nci(self.cppcode, 4))

        cppfile.write("}\n\n")


class Function(FunctionBase):
    PREFIX = 'wrappedfunc_'
    def __init__(self, func, parent):
        super(Function, self).__init__(func, parent)

class Method(FunctionBase):
    PREFIX = 'wrappedmeth_'

    def __eq__(self, other):
        """
        Two methods are equal when they have the same C++ signature.
        """
        if not isinstance(other, Method):
            return False
        if ((self.name != other.name) or
            (len(self.params) != len(other.params)) or
            (self.virtual is not other.virtual) or
            (self.const is not other.const) or
            (self.type != other.type)):
            return False
        return all(p == other.params[i] for i, p in enumerate(self.params))
        #for i, p in enumerate(self.params):
        #    if p != other.params[i]:
        #        return False
        #return True

    def copy(self, newparent):
        vmeth = type(self).__new__(type(self))
        vmeth.__dict__.update(self.__dict__)
        vmeth.parent = newparent

        return vmeth

class CppMethod(Method):
    def __init__(self, meth, parent):
        super(CppMethod, self).__init__(meth, parent)

        self.cppcode = meth.body

    def setup(self):
        super(CppMethod, self).setup()
        self.extract_params()

    def extract_params(self):
        """
        CppMethodDefs are always specified with an empty parameter list. So
        that they may be treated like regular FunctionDefs where ever possible,
        this method will disassemble their args string into a list of Params.
        Based loosely on the extractors.FunctionDef.makePyArgsString
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


class CppMethod_cffi(Method):
    def __init__(self, meth, parent):
        super(CppMethod_cffi, self).__init__(meth, parent)

        self.cppcode = meth.body
        self.c_args = meth.argsString

    def print_cppcode(self, cppfile):
        cppfile.write(nci("""\
        WL_INTERNAL {0.type.cdef_type} {0.cname}{0.c_args}
        {{""".format(self)))

        cppfile.write(nci(self.cppcode, 4))

        cppfile.write("}\n\n")

#----------------------------------------------------------------------------#

def create_function(func, parent):
    Function(func, parent)
extractors.FunctionDef.generate = create_function

def create_method(meth, parent):
    Method(meth, parent)
extractors.MethodDef.generate = create_method

def create_cppmethod(meth, parent):
    CppMethod(meth, parent)
extractors.CppMethodDef.generate = create_cppmethod

def create_cppmethod_cffi(meth, parent):
    CppMethod_cffi(meth, parent)
extractors.CppMethodDef_cffi.generate = create_cppmethod_cffi
