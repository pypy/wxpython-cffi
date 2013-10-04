from base import CppObject

from .. import extractors

class Param(CppObject):
    pass

class FunctionBase(CppObject):
    pass

class Function(FunctionBase):
    def __init__(self, func, parent):
        self.func = func

class Method(FunctionBase):
    def __init__(self, meth, parent):
        self.meth = meth

class CppMethod(Method):
    pass

class CppMethod_cffi(Method):
    pass

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

