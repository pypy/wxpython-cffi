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
        self.instancecheck_code = cls.instanceCheck or 'pass'
        self.convert_to_c_code = cls.py2c or 'pass'
        self.convert_to_py_code = cls.c2py or 'pass'

        self.to_c_code = cls.cpp2c
        self.to_c_name = 'WL_mappedtype<{0.name}, {0.ctype}>::to_c'.format(self)
        self.to_c_array_name = self.to_c_name + '_array'

        self.to_cpp_code = cls.c2cpp
        self.to_cpp_name = self.to_c_name + 'pp'
        self.to_cpp_array_name = self.to_cpp_name + '_array'

        self.to_cpp_cdefname = self.name + '_to_cpp'

        self.default_placeholder = cls.placeHolder

    def build_typeinfo(self, typeinfo):
        typeinfo.c_type = self.ctype
        typeinfo.cdef_type = self.ctype
        typeinfo.c_virt_return_type = self.ctype
        typeinfo.cdef_virt_return_type = self.ctype

        pytypes = [self.unscopedpyname]
        if typeinfo.ptrcount:
            pytypes.append('types.NoneType')
        typeinfo.py_type = '(' + ', '.join(pytypes) + ')'

        if not typeinfo.flags.inout and (typeinfo.ptrcount == 2 or
           typeinfo.refcount and typeinfo.ptrcount):
            # By default T** and T&* parameters are out
            typeinfo.flags.out = True

        if typeinfo.flags.out or typeinfo.flags.inout:
            # T** is needed when using out so C++ can write into the pointer
            # Python is holding.
            typeinfo.c_type += '*'
            typeinfo.cdef_type += '*'

        if typeinfo.flags.array:
            typeinfo.c_type += ' *'
            typeinfo.cdef_type += '[]'
            typeinfo.py_type = ('wrapper_lib.create_array_type(%s, ctype="%s")'
                                % (self.name, typeinfo.cdef_type))

        typeinfo.c_virt_type = typeinfo.c_type
        typeinfo.cdef_virt_type = typeinfo.cdef_type

        typeinfo.default_placeholder = self.default_placeholder

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("""\
        class {0.pyname}(wrapper_lib.MappedBase):
            @classmethod
            def __instancecheck__(cls, py_obj):
        """.format(self), indent))
        pyfile.write(nci(self.instancecheck_code, indent + 8))

        pyfile.write(nci("""\
            @classmethod
            def to_py(cls, cdata):
        """, indent + 4))
        pyfile.write(nci(self.convert_to_py_code, indent + 8))

        pyfile.write(nci("""\
            @classmethod
            def to_c(cls, py_obj):
                if py_obj is None:
                    return ffi.NULL
        """, indent + 4))
        pyfile.write(nci(self.convert_to_c_code, indent + 8))

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

    def call_cdef_param_setup(self, typeinfo, name):
        if typeinfo.flags.out:
            return "{0}{1.OUT_PARAM_SUFFIX} = ffi.new('{1.cdef_type}')".format(
                    name, typeinfo)
        if typeinfo.flags.inout:
            return """\
            {0} = {1.unscopedpyname}.to_c({0})
            {0}{2.OUT_PARAM_SUFFIX} = ffi.new('{2.cdef_type}', {0})
            """.format(name, self, typeinfo)
        if typeinfo.flags.array:
            return ("{0}, {1.ARRAY_SIZE_PARAM}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2.unscopedpyname}, ctype='{1.cdef_type}').to_c({0})"
                    .format(name, typeinfo, self))
        return "{0} = {1}.to_c({0})".format(name, self.unscopedpyname)

    def call_cdef_param_inline(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return name + typeinfo.OUT_PARAM_SUFFIX
        return name

    def call_cpp_param_setup(self, typeinfo, name):
        if typeinfo.flags.hasdefault:
            # XXX raise Exception()
            return '{0} *{1}_converted = NULL;'.format(self.name, name)

        if typeinfo.flags.out:
            isptr = '*' if ((typeinfo.refcount and typeinfo.ptrcount == 1) or
                            typeinfo.ptrcount == 2) else ''
            return '{0} {1}{2}_converted;'.format(self.name, isptr, name)

        if typeinfo.flags.array:
            return "{0.name} *{1}_converted = {0.to_cpp_array_name}({1}, {2});".format(
                self, name, typeinfo.ARRAY_SIZE_PARAM)

        deref = '*' if typeinfo.flags.inout else ''
        return '{0.name} *{1}_converted = {0.to_cpp_name}({2}{1});'.format(
            self, name, deref)

    def call_cpp_param_inline(self, typeinfo, name):
        deref = not typeinfo.ptrcount

        if typeinfo.flags.hasdefault:
            return '{0}_converted = {1}({2}{0});'.format(
                name, self.to_cpp_name, deref)
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
        # If transfering the mapped type, don't delete it. This is a sip
        # behavior that isn't particularly well documented.
        if not typeinfo.flags.transfer:
            return 'delete %s_converted;' % name

    def virt_py_param_inline(self, typeinfo, name):
        if typeinfo.flags.array:
            return ("wrapper_lib.create_array_type({0}, ctype='{1.cdef_type}').to_py({2}, {1.ARRAY_SIZE_PARAM})"
                    .format(self.unscopedpyname, typeinfo, name))

        deref = '[0]' if typeinfo.flags.inout else ''
        return "%s.to_py(%s%s)" % (self.unscopedpyname, name, deref)

    def virt_py_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            return ('{0}[0] = {1.unscopedpyname}.to_c({0}{2})'
                    .format(name, self, typeinfo.PY_RETURN_SUFFIX))

    def virt_py_return(self, typeinfo, name):
        return ('{0} = {1.unscopedpyname}.to_c({0})'
                .format(name, self))

    def virt_cpp_param_setup(self, typeinfo, name):
        if typeinfo.flags.out:
            return "{0} {1}_converted;".format(typeinfo.c_virt_return_type, name)
        if typeinfo.flags.inout:
            return "{0} {1}_converted = {2}({1});".format(
                typeinfo.c_virt_return_type, name, self.to_c_name)

    def virt_cpp_param_inline(self, typeinfo, name):
        if typeinfo.flags.array:
            return "%s(%s, %s)" % (self.to_c_array_name, name,
                                   typeinfo.ARRAY_SIZE_PARAM)

        if typeinfo.flags.out or typeinfo.flags.inout:
            return '&' + name + "_converted"
        return '%s(%s)' % (self.to_c_name, name)

    def virt_cpp_param_cleanup(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            if typeinfo.ptrcount == 2: # T**
                return "*{0} = {1.to_cpp_name}({0}_converted);".format(name,
                                                                       self)
            elif typeinfo.ptrcount and typeinfo.refcount: # T*&
                return "{0} = {1.to_cpp_name}({0}_converted);".format(name,
                                                                      self)
            elif typeinfo.ptrcount and not typeinfo.refcount: # T*
                return ("*{0} = *WL_AutoDelPtr<{1.name}>({1.to_cpp_name}({0}_converted));"
                        .format(name, self))
            elif not typeinfo.ptrcount and typeinfo.refcount: # T&
                return ("{0} = *WL_AutoDelPtr<{1.name}>({1.to_cpp_name}({0}_converted));"
                        .format(name, self))

    def virt_cpp_return(self, typeinfo, name):
        deref = '*' if not typeinfo.ptrcount else ''
        return '%s%s(%s)' % (deref, self.to_cpp_name, name)

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return '%s(%s)' % (self.to_c_name, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        if typeinfo.flags.out or typeinfo.flags.inout:
            name = name + typeinfo.OUT_PARAM_SUFFIX + '[0]'
        return '%s.to_py(%s)' % (self.unscopedpyname, name)
