
import re
import sys
import warnings
from binascii import crc32

from .base import CppType

import etgtools.extractors as extractors

# C basic types -> Python conversion functions
BASIC_CTYPES = {
    '' : 'int', # unsigned
    'int': 'int',
    'short': 'int',
    'long': 'int',
    'long long': 'int',
    'signed': 'int',
    'unsigned': 'int',
    'size_t' : 'int',
    'ssize_t' : 'int',
    'float': 'float',
    'double': 'float',
    'char': 'str',
    'wchar_t': 'unicode',
    'char': 'str',
    'bool': 'bool',
}

def getbasictype(name, typeinfo):
    if name == 'void' and typeinfo.ptrcount:
        return VoidPtrType()
    elif name in ('', None, 'void'):
        return VoidType()
    elif typeinfo.ptrcount and 'char' in name:
        # One length strings (ie `char`) are not StringType
        return StringType(name)
    elif (name in BASIC_CTYPES or
            name.replace('unsigned ', '').strip() in BASIC_CTYPES or
            name.replace('signed ', '').strip() in BASIC_CTYPES):
        return BasicType(name)
    else:
        return None

class BasicType(CppType):
    _cache = {}
    def __new__(cls, name):
        if name in cls._cache:
            return cls._cache[name]

        type = super(BasicType, cls).__new__(cls, name)
        cls._cache[name] = type
        return type

    def __init__(self, name):
        self.name = name
        self.unscopedname = name

        self.stripped_name = (self.name.replace('unsigned ', '')
                              .replace('signed ', '').strip())

        self.unscopedpyname = BASIC_CTYPES[self.stripped_name]

    is_char_re = re.compile(r'(^| )char\s*$')
    @property
    def is_char(self):
        return self.is_char_re.search(self.name) is not None

    def build_typeinfo(self, typeinfo):
        if typeinfo.flags.array:
            raise TypeError('use of the Array annotation is unsupported on '
                            "'%s' parameters" % typeinfo.original)

        if typeinfo.flags.pyint and not self.is_char:
            raise TypeError('use of the PyInt annotation is unsupported on '
                            "'%s' parameters" % typeinfo.original)

        typeinfo.type = self

        # self.name is the stripped name of the type, ie const, etc. removed
        typeinfo.c_type = self.name
        typeinfo.cdef_type = self.name

        if typeinfo.const and 'const ' not in typeinfo.c_type:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        if typeinfo.name == 'bool':
            # MSVC doesn't support _Bool, so pass bools as ints through cffi
            typeinfo.c_type = 'int'
            typeinfo.cdef_type = 'int'

        if (typeinfo.ptrcount or typeinfo.refcount) and not typeinfo.flags.inout:
            typeinfo.flags.out = True

        if not (typeinfo.flags.out or typeinfo.flags.inout):
            typeinfo.c_virt_type = typeinfo.c_type
            typeinfo.cdef_virt_type = typeinfo.cdef_type
        else:
            typeinfo.c_virt_type = typeinfo.c_type + '*'
            typeinfo.cdef_virt_type = typeinfo.cdef_type + '*'
        typeinfo.c_virt_return_type = typeinfo.c_type
        typeinfo.cdef_virt_return_type = typeinfo.cdef_type

        # The only way we will put a '*' on basic type if its an out variable.
        # We do not handle pointers to basic types otherwise
        if typeinfo.flags.out or typeinfo.flags.inout:
            typeinfo.c_type += '*'
            typeinfo.cdef_type += '*'

        typeinfo.py_type = 'numbers.Number'
        typeinfo.default_placeholder = '0'
        if not typeinfo.flags.pyint and self.is_char:
            # Treat all non-pyint chars as strings.
            # TODO: This is actually incorrect, we should only accept length 1
            #       strings. Add type to wrapper_lib to handle this
            typeinfo.py_type = '(__builtin__.str, __builtin__.unicode)'
            typeinfo.default_placeholder = "''"

        typeinfo.wrapper_type = typeinfo.cpp_type.strip('&*')

        typeinfo.default_placeholder = '0'

    def call_cdef_param_setup(self, typeinfo, name):
        if typeinfo.flags.out:
            return ("{0}{1.CFFI_PARAM_SUFFIX} = ffi.new('{1.cdef_type}')"
                    .format(name, typeinfo))

        if typeinfo.flags.inout:
            return """\
            {0}{2.CFFI_PARAM_SUFFIX} = ffi.new('{2.cdef_type}', {1}({0}))
            """.format(name, BASIC_CTYPES[self.stripped_name], typeinfo)

        assign = name + typeinfo.CFFI_PARAM_SUFFIX + ' = '

        if self.is_char:
            if 'signed ' in self.name:
                # CFFI expects an int
                if typeinfo.flags.pyint:
                    return assign + '__builtin__.int(%s)' % name
                else:
                    return assign + '__builtin__.ord(%s)' % name
            else:
                # CFFI expects a length-1 string
                if typeinfo.flags.pyint:
                    return assign + '__builtin__.chr(%s)' % name
                else:
                    return assign + '__builtin__.str(%s)' % name

        return assign + "__builtin__.%s(%s)" % (BASIC_CTYPES[self.stripped_name], name)

    def virt_py_param_inline(self, typeinfo, name):
        if typeinfo.flags.inout:
            return name + '[0]'
        return name

    def virt_py_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            # For out and inout cases, we're writing into a pointer
            return "{0}[0] = __builtin__.{1}({0}{2.PY_RETURN_SUFFIX})".format(
                        name, BASIC_CTYPES[self.stripped_name], typeinfo)

    def virt_cpp_param_inline(self, typeinfo, name):
        ref = '&' if typeinfo.refcount else ''
        return ref + name


    def virt_cpp_return(self, typeinfo, name):
        return name

    def call_cpp_param_inline(self, typeinfo, name):
        if self.name == 'bool':
            ptr = '*' if typeinfo.ptrcount or typeinfo.refcount else ''
            name = "(bool %s)%s" % (ptr, name)
        if typeinfo.refcount:
            assert typeinfo.flags.out or typeinfo.flags.inout
            return '*' + name
        return name

    def convert_variable_cpp_to_c(self, typeinfo, name):
        if typeinfo.refcount:
            return '&' + name
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return '%s%s[0]' % (name, typeinfo.CFFI_PARAM_SUFFIX)

        if self.is_char:
            if 'signed ' in self.name:
                # CFFI gives us an int
                if typeinfo.flags.pyint:
                    return name
                else:
                    return '__builtin__.chr(%s)' % name
            else:
                # CFFI gives us a length-1 string
                if typeinfo.flags.pyint:
                    return '__builtin__.ord(%s)' % name
                else:
                    return name

        return "%s(%s)" % (BASIC_CTYPES[self.stripped_name], name)

    def user_cpp_param_inline(self, typeinfo, name):
        # Basic types are always handled as regular values.
        deref = '*' * typeinfo.ptrcount
        return deref + name

    def user_cpp_return(self, typeinfo, name):
        # We don't support return values of T* or T& basic types, so there's
        # nothing special to do here.
        return name

class StringType(CppType):
    _cache = {}
    def __new__(cls, name):
        signedness = int('signed ' in name) - 2*int('unsigned ' in name)
        unicodeness = 'wchar_t' in name
        identifier = (signedness, unicodeness)

        if identifier in cls._cache:
            return cls._cache[(identifier)]

        type = super(StringType, cls).__new__(cls, name)
        cls._cache[name] = type

        type.signed = signedness
        type.unicode = unicodeness

        return type

    def __init__(self, name):
        self.name = name
        self.unscopedname = name

    def build_typeinfo(self, typeinfo):
        if self.signed == 1:
            typeinfo.c_type = 'signed '
        elif self.signed == 0:
            typeinfo.c_type = ''
        elif self.signed == -1:
            typeinfo.c_type = 'unsigned '

        if self.unicode:
            typeinfo.c_type += 'wchar_t *'
        else:
            typeinfo.c_type += 'char *'

        typeinfo.cdef_type = typeinfo.c_type

        if typeinfo.const:
            typeinfo.c_type = 'const ' + typeinfo.c_type

        typeinfo.py_type = '(__builtin__.unicode, __builtin__.str)'
        typeinfo.default_placeholder = ''

        typeinfo.c_virt_return_type = typeinfo.c_type
        typeinfo.cdef_virt_return_type = typeinfo.cdef_type

        typeinfo.c_virt_type = typeinfo.c_type
        typeinfo.cdef_virt_type = typeinfo.cdef_type

        typeinfo.wrapper_type = typeinfo.cpp_type

        typeinfo.default_placeholder = 'ffi.NULL'

    def call_cdef_param_setup(self, typeinfo, name):
        if not self.unicode:
            conversion = '__builtin__.str'
        else:
            conversion = '__builtin__.unicode'
        return '{0}{1.CFFI_PARAM_SUFFIX} = {2}({0})'.format(name, typeinfo,
                                                            conversion)

    def virt_py_return(self, typeinfo, name):
        if not self.unicode:
            conversion = 'str'
        else:
            conversion = 'unicode'
        return '{0} = wrapper_lib.allocate_c{1}({0}, clib)'.format(name,
                                                                   conversion)

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return 'ffi.string(%s)' % name

    def user_cpp_param_inline(self, typeinfo, name):
        # String types are passed as pointers and we only support strings as
        # pointers.
        return name

    def user_cpp_return(self, typeinfo, name):
        # See above.
        return name

class VoidPtrType(CppType):
    def __new__(cls):
        # Only one instance of VoidPtrType needed/wanted.
        if not hasattr(cls, '_inst'):
            cls._inst = super(cls, cls).__new__(cls)

        return cls._inst

    def __init__(self):
        self.name = 'void *'
        self.unscopedname = 'void *'

    def build_typeinfo(self, typeinfo):
        const = 'const ' if typeinfo.const else ''

        typeinfo.c_type = typeinfo.cdef_type = const + 'void *'

        if not (typeinfo.flags.out or typeinfo.flags.inout):
            typeinfo.c_virt_type = typeinfo.cdef_virt_type = const + 'void *'
        else:
            typeinfo.c_virt_type = typeinfo.cdef_virt_type = const + 'void **'

        typeinfo.c_virt_return_type = typeinfo.c_type
        typeinfo.cdef_virt_return_type = typeinfo.cdef_type

        typeinfo.py_type = 'object'

        # Set the ptrcount to zero since it is implicit in being VoidPtrType.
        # This simplifies some code in other places.
        typeinfo.ptrcount = 0

        typeinfo.wrapper_type = const + 'void*'

    def call_cdef_param_setup(self, typeinfo, name):
        return name + typeinfo.CFFI_PARAM_SUFFIX + ' = ' + name

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return name

    def user_cpp_param_inline(self, typeinfo, name):
        # Void pointers are by there nature opaque.
        return name

    def user_cpp_return(self, typeinfo, name):
        # See above.
        return name

class VoidType(CppType):
    def __new__(cls):
        if not hasattr(cls, '_inst'):
            cls._inst = super(cls, cls).__new__(cls)

        return cls._inst

    def __init__(self):
        self.name = 'void'
        self.unscopedname = 'void'
        pass

    def build_typeinfo(self, typeinfo):
        typeinfo.c_type = typeinfo.cdef_type = 'void'

        typeinfo.c_virt_type = typeinfo.c_type
        typeinfo.cdef_virt_type = typeinfo.cdef_type
        typeinfo.c_virt_return_type = typeinfo.c_type
        typeinfo.cdef_virt_return_type = typeinfo.cdef_type

        typeinfo.wrapper_type = 'void'

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return name

    def convert_variable_c_to_py(self, typeinfo, name):
        return name

