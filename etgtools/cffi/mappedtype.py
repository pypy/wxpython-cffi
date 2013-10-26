from .base import CppType

from .utils import nci

from .. import extractors

def create_mappedtype(mtype, parent):
    MappedType(mtype, parent)
extractors.MappedTypeDef_cffi.generate = create_mappedtype

class MappedType(CppType):
    def __init__(self, cls, parent):
        super(MappedType, self).__init__(cls, parent)

        self.ctype = cls.cType

        self.to_c_code = cls.cpp2c
        self.to_c_name = 'WL_mappedtype<{0.name}, {0.ctype}>::to_c'.format(self)
        self.to_c_array_name = self.to_c_name + '_array'

        self.to_cpp_code = cls.c2cpp
        self.to_cpp_name = self.to_c_name + 'pp'
        self.to_cpp_array_name = self.to_cpp_name + '_array'

        self.to_cpp_cdefname = self.name + '_to_cpp'


    def build_typeinfo(self, typeinfo):
        typeinfo.c_type = self.ctype
        typeinfo.cdef_type = self.ctype
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

    def print_cppcode(self, cppfile):
        cppfile.write(nci("""\
        template<>
        {0.ctype} WL_mappedtype<{0.name}, {0.ctype}>::
            to_c({0.name} *cpp_obj)
        {{
{1}
        }}

        template<>
        {0.name} * WL_mappedtype<{0.name}, {0.ctype}>::
            to_cpp({0.ctype} cdata)
        {{
{2}
        }}

        extern "C" {0.name} * {0.to_cpp_cdefname}({0.ctype} cdata)
        {{
            return WL_mappedtype<{0.name}, {0.ctype}>::to_cpp(cdata);
        }}
        """.format(self, nci(self.to_c_code, 12), nci(self.to_cpp_code, 12))))

    def call_cpp_param_setup(self, typeinfo, name):
        if typeinfo.flags.out:
            isptr = '*' if ((typeinfo.refcount and typeinfo.ptrcount == 1) or
                            typeinfo.ptrcount == 2) else ''
            #    return '{0} *{1}_converted;'.format(self.name, name)
            #else:
            #    return '{0} {1}_converted;'.format(self.name, name)
            return '{0} {1}{2}_converted;'.format(self.name, isptr, name)

        if typeinfo.flags.array:
            return "{0} {1}_converted = {2}({1}, {3});".format(
                typeinfo.c_virt_return_type, name, self.to_cpp_array_name,
                ARRAY_SIZE_PARAM)

        deref = '*' if typeinfo.flags.inout else ''
        return '{0} {1}_converted = {2}({3}{1});'.format(
            typeinfo.c_virt_return_type, name, self.to_cpp_name, deref)

    def call_cpp_param_inline(self, typeinfo, name):
        name += '_converted'
        if typeinfo.flags.array:
            return name

        if typeinfo.flags.out:
            if typeinfo.refcount:
                return name
            else:
                return '&' + name

        if typeinfo.flags.inout:
            if typeinfo.refcount:
                return '*' + name
            else:
                return name

        # TODO: refsAsPtrs?
        #deref = not self.isPtr and not (self.isRef and refsAsPtrs)
        deref = not typeinfo.ptrcount
        return ('*' if deref else '') + name

    def call_cpp_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.array:
            if typeinfo.flags.transfer:
                return None
            return 'delete[] %s_converted;' % name

        if typeinfo.flags.inout:
            return """\
            *{0} = {1}({0}_converted);
            delete {0}_converted;
            """.format(name, self.to_c_name)
        if typeinfo.flags.out:
            return "*{0} = {1}({0}_converted);".format(name, self.to_c_name)
        # TODO: if transfering the mapped type, don't delete it?
        #       Test if sip actually doesn't delete in this case
        return 'delete %s_converted;' % name

    def virt_cpp_param_setup(self, typeinfo, name):
        pass

    def virt_cpp_param_inline(self, typeinfo, name):
        return name

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
        return '%s(%s)' % (self.to_c_name, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        #if typeinfo.flags.out or typeinfo.flags.inout:
        #    return '%s.c2py(%s[0])' % (self.unscopedpyname, name)
        #if typeinfo.flags.array:
        #    return ("wrapper_lib.create_array_type({2}, ctype='{3}').c2py({0}, {1})"
        #            .format(varName, ARRAY_SIZE_PARAM,
        #                    self.typedef.unscopedPyName, self.cdefType))
        return '%s.c2py(%s)' % (self.unscopedpyname, name)
