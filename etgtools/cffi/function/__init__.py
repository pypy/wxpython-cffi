from .function import *
from .method import *
from .static_method import *
from .cpp_method import *
from .ctor import *
from .dtor import *


from ..wrappedtype import WrappedType
from ... import extractors

def create_function(func, parent):
    Function(func, parent)
extractors.FunctionDef.generate = create_function

def create_method(meth, parent):
    if meth.isStatic:
        return StaticMethod(meth, parent)
    if meth.isCtor:
        return CtorMethod(meth, parent)
    if meth.isDtor:
        return DtorMethod(meth, parent)
    return Method(meth, parent)
extractors.MethodDef.generate = create_method

def create_cppmethod(meth, parent):
    if isinstance(parent, WrappedType):
        if meth.isCtor:
            return CppCtorMethod(meth, parent)
        return MemberCppMethod(meth, parent)
    else:
        return GlobalCppMethod(meth, parent)
extractors.CppMethodDef.generate = create_cppmethod

def create_cppmethod_cffi(meth, parent):
    if isinstance(parent, WrappedType):
        if meth.isCtor:
            return CppCtorMethod_cffi(meth, parent)
        return MemberCppMethod_cffi(meth, parent)
    else:
        return GlobalCppMethod_cffi(meth, parent)
extractors.CppMethodDef_cffi.generate = create_cppmethod_cffi
