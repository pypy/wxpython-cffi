
import sys
from binascii import crc32

from .base import CppType

import etgtools.extractors as extractors

# C basic types -> Python conversion functions
BASIC_CTYPES = {
    'int': 'int',
    'short': 'int',
    'long': 'int',
    'long long': 'int',
    'unsigned': 'int',
    'size_t' : 'int',
    'ssize_t' : 'int',
    'float': 'float',
    'double': 'float',
    'char': 'str',
    'wchar_t': 'unicode',
    'char*': 'str',
    'char *': 'str',
    'signed char': 'int',
    'unsigned char': 'int',
    'bool': 'bool',
}


ARRAY_SIZE_PARAM = 'array_size_'
OUT_PARAM_SUFFIX = '_ptr'

def getbasictype(name, typeinfo):
    if name == 'void' and typeinfo.ptrcount:
        return VoidPtrType()
    elif name in ('', None, 'void'):
        return VoidType()
    elif typeinfo.ptrcount and 'char' in name:
        return StringType(name)
    elif (name in BASIC_CTYPES or
            name.replace('unsigned ', '').strip() in BASIC_CTYPES or
            name.replace('signed ', '').strip() in BASIC_CTYPES):
        return BasicType(name)
    else:
        return None

class BasicType(CppType):
    c_virtual_type = property(lambda self: self.c_type)
    c_virtual_return_type = property(lambda self: self.c_type)
    cdef_virtual_type = property(lambda self: self.cdef_type)
    cdef_virtual_return_type = property(lambda self: self.cdef_type)

    _cache = {}
    def __new__(cls, name):
        if name in cls._cache:
            return cls._cache[name]

        if not name in BASIC_CTYPES:
            raise UnknownTypeException(name)

        type = super(BasicType, cls).__new__(cls, name)
        cls._cache[name] = type
        return type

    def __init__(self, name):
        self.name = name

    def build_typeinfo(self, typeinfo):
        if typeinfo.flags.array:
            raise TypeError('use of the Array annotation is unsupported on '
                            "'%s' parameters" % typeinfo.original)

        if typeinfo.flags.pyint and 'char' not in typeinfo.name:
            raise TypeError('use of the PyInt annotation is unsupported on '
                            "'%s' parameters" % typeinfo.original)

        #if isinstance(typedef, extractors.TypedefDef):
        #    assert typedef.platformDependent
        #    BASIC_CTYPES[typedef.name] = BASIC_CTYPES[typedef.type]

        typeinfo.type = self

        # self.name is the stripped name of the type, ie const, etc. removed
        typeinfo.c_type = self.name
        typeinfo.cdef_type = self.name

        if typeinfo.flags.pyint and not 'signed' in self.name:
            typeinfo.cdef_type = typeinfo.cdef_type.replace('char', 'signed char')

        if typeinfo.const and 'const ' not in typeinfo.c_type:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        if typeinfo.name == 'bool':
            # MSVC doesn't support _Bool, so pass bools as into through cffi
            typeinfo.c_type = 'int'
            typeinfo.cdef_type = 'int'

        if (typeinfo.ptrcount or typeinfo.refcount) and not typeinfo.flags.inout:
            typeinfo.flags.out = True

        # The only way we will put a '*' on basic type if its an out variable.
        # We do not handle pointers to basic types otherwise
        if typeinfo.flags.out or typeinfo.flags.inout:
            typeinfo.c_type += '*'
            typeinfo.cdef_type += '*'

        typeinfo.py_type = 'numbers.Number'
        typeinfo.default_placeholder = '0'
        if not typeinfo.flags and 'char' in self.name:
            # Treat all non-pyint chars as strings.
            # TODO: This is actually incorrect, we should only accept length 1
            #       strings. Add type to wrapper_lib to handle this
            typeinfo.py_type = '(__builtin__.str, __builtin__.unicode)'
            typeinfo.default_placeholder = "''"

        typeinfo.default_placeholder = '0'

    def convert_variable_cpp_to_c(self, typeinfo, name):
        if typeinfo.refcount:
            return '&' + name
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return "%s(%s)" % (BASIC_CTYPES[self.name], name)

class StringType(CppType):
    _cache = {}
    def __new__(cls, name):
        if name in cls._cache:
            return cls._cache[name]

        assert name in ('char', 'wchar_t')

        type = super(StringType, cls).__new__(cls, name)
        cls._cache[name] = type
        return type

    def __init__(self, name):
        self.name = name

    def build_typeinfo(self, typeinfo):
        #if self.isConst:
        #    self.name = 'const ' + self.name

        typeinfo.c_type = self.name + '*'
        typeinfo.cdef_type = typeinfo.c_type

        if typeinfo.const:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        typeinfo.py_type = '(__builtin__.unicode, __builtin__.str)'
        typeinfo.default_placeholder = ''

        # TODO: Figure out what the correct choice is here when it comes up.
        #       The code from the pre-refactor below is definately wrong.
        #typeinfo.c_virt_return_type = self.name
        #typeinfo.cdef_virt_return_type = self.name

        typeinfo.c_virt_type = typeinfo.c_type
        typeinfo.cdef_virt_type = typeinfo.cdef_type

        typeinfo.default_placeholder = 'ffi.NULL'

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return 'ffi.string(%s)' % name

class VoidPtrType(CppType):
    def __new__(cls):
        # Only one instance of VoidPtrType needed/wanted.
        if not hasattr(cls, '_inst'):
            cls._inst = super(cls, cls).__new__(cls)

        return cls._inst

    def __init__(self):
        pass

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return name

class VoidType(CppType):
    def __new__(cls):
        if not hasattr(cls, '_inst'):
            cls._inst = super(cls, cls).__new__(cls)

        return cls._inst

    def __init__(self):
        pass

    def build_typeinfo(self, typeinfo):
        typeinfo.c_type = typeinfo.cdef_type = 'void'

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return name

