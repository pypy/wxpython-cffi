from .base import CppType

from .. import extractors

def create_mappedtype(mtype, parent):
    MappedType(mtype, parent)
extractors.MappedTypeDef_cffi.generate = create_mappedtype

class MappedType(CppType):
    def __init__(self, cls, parent):
        super(MappedType, self).__init__(cls, parent)

    def build_typeinfo(self, original, name, flags):
        typeinfo.c_type = self.item.cType
        typeinfo.cdef_type = self.item.cType
        typeinfo.c_virt_return_type = self.name + '*'
        typeinfo.cdef_virt_return_type = 'void *'

        pytypes = [self.unscopedpyname]
        if typeinfo.ptrcount:
            pytypes.append('types.NoneType')
        typeinfo.py_type = '(' + ', '.join(pytypes) + ')'

        if not typeinfo.flags.inout and (typeinfo.ptrcount == 2 or
           typeinfo.refcount and typeinfo.ptrcount):
            # By default T** and T&* parameters are out
            typeinfo.flags.out = True

        if typeinfo.flags.out or typeinfo.flags.inout:
            # A ** is needed when using out so C++ can write into the pointer
            # Python is holding.
            typeinfo.c_type += '*'
            typeinfo.cdef_type += '*'

        if typeinfo.flags.array:
            typeinfo.c_type += ' *'
            typeinfo.cdef_type += '[]'
            typeinfo.py_type = ('wrapper_lib.create_array_type(%s, ctype="%s")'
                                % (self.name, typeinfo.cdef_type))

        if typeinfo.flags.out:
            # When using an out paremeter, the type for the callback signature
            # needs to be ** so Python can write into the C++ pointer
            typeinfo.c_virt_type = self.name + '**'
            typeinfo.cdef_virt_type = "void **"
        else:
            typeinfo.c_virt_type = typeinfo.c_type
            typeinfo.cdef_virt_type = typeinfo.cdef_type
