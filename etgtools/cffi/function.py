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

