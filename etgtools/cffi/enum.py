from .base import CppType, CppObject, TypeInfo
from .variable import VariableBase

from .basictype import BasicType, getbasictype

from .. import extractors

def create_enum(enum, parent):
    Enum(enum, parent)
extractors.EnumDef.generate = create_enum

class Enum(CppType):
    def __init__(self, enum, parent):
        # Take enum values and put them into the parent scope
        super(Enum, self).__init__(enum, parent)

        self.type = BasicType('int')
        for val in enum.items:
            EnumValue(val, parent)

    def build_typeinfo(self, typeinfo):
        self.type.build_typeinfo(typeinfo)

        typeinfo.type = self

    def call_cdef_param_setup(self, typeinfo, name):
        return self.type.call_cdef_param_setup(typeinfo, name)

    def call_cdef_param_inline(self, typeinfo, name):
        return self.type.call_cdef_param_inline(typeinfo, name)

    def call_cdef_param_cleanup(self, typeinfo, name):
        return self.type.call_cdef_param_cleanup(typeinfo, name)

    def virt_py_param_setup(self, typeinfo, name):
        return self.type.virt_py_param_setup(typeinfo, name)

    def virt_py_param_inline(self, typeinfo, name):
        return self.type.virt_py_param_inline(typeinfo, name)

    def virt_py_param_cleanup(self, typeinfo, name):
        return self.type.virt_py_param_cleanup(typeinfo, name)

    def virt_py_return(self, typeinfo, name):
        return self.type.virt_py_return(typeinfo, name)

    def call_cpp_param_setup(self, typeinfo, name):
        return self.type.call_cpp_param_setup(typeinfo, name)

    def call_cpp_param_inline(self, typeinfo, name):
        ret = self.type.call_cpp_param_inline(typeinfo, name)

        # int -> enum conversions aren't implicit in C++, so we need a cast
        return "(%s)" % self.unscopedname + ret

    def call_cpp_param_cleanup(self, typeinfo, name):
        return self.type.call_cpp_param_cleanup(typeinfo, name)

    def virt_cpp_param_setup(self, typeinfo, name):
        return self.type.virt_cpp_param_setup(typeinfo, name)

    def virt_cpp_param_inline(self, typeinfo, name):
        return self.type.virt_cpp_param_inline(typeinfo, name)

    def virt_cpp_param_cleanup(self, typeinfo, name):
        return self.type.virt_cpp_param_cleanup(typeinfo, name)

    def virt_cpp_return(self, typeinfo, name):
        return self.type.virt_cpp_return(typeinfo, name)

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return self.type.convert_variable_cpp_to_c(typeinfo, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        return self.type.convert_variable_c_to_py(typeinfo, name)

class EnumValue(VariableBase):
    PREFIX = 'cffienumval'
    def __init__(self, val, parent):
        super(EnumValue,self).__init__(val, parent)
        self.type = 'const long long'

    def setup(self):
        self.type = TypeInfo(self.parent, self.type, self.flags)
