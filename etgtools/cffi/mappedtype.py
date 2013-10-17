from .base import CppType

from .. import extractors

def create_mappedtype(mtype, parent):
    MappedType(mtype, parent)
extractors.MappedTypeDef_cffi.generate = create_mappedtype

class MappedType(CppType):
    def __init__(self, cls, parent):
        super(MappedType, self).__init__(cls, parent)

        self.cpp2cfunc = 'cfficonvert_mappedtype<%s>' % self.name

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

    def call_cpp_param_setup(self, typeinfo, name):
        pass

    def call_cpp_param_inline(self, typeinfo, name):
        pass

    def call_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_param_setup(self, typeinfo, name):
        pass

    def virt_cpp_param_inline(self, typeinfo, name):
        pass

    def virt_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_return_setup(self, typeinfo, name):
        pass

    def virt_cpp_return_cleanup(self, typeinfo, name):
        pass

    def convert_variable_cpp_to_c(self, typeinfo, name):
        # TODO: do these belong here or somewhere else?
        #if self.array:
        #    return "%s(%s, %s)" % (self.typedef.arraycpp2c, varName,
        #                           ARRAY_SIZE_PARAM)

        #if typeinfo.flags.out:
        #    if self.ptrCount == 2:
        #        return name
        #    if  self.isRef and self.isPtr:
        #        return '&' + name
        #    else:
        #        return '&' + name + "_ptr"
        #if typeinfo.flags.inout:
        #    return '&' + varName + "_converted"
        return '%s(%s)' % (self.cpp2cfunc, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return '%s.c2py(%s[0])' % (self.unscopedpyname, name)
        #if typeinfo.flags.array:
        #    return ("wrapper_lib.create_array_type({2}, ctype='{3}').c2py({0}, {1})"
        #            .format(varName, ARRAY_SIZE_PARAM,
        #                    self.typedef.unscopedPyName, self.cdefType))
        return '%s.c2py(%s)' % (self.typedef.unscopedPyName, varName)
