import utils

from .utils import nci
from .base import CppType, TypeInfo, ItemFlags
from .wrappedtype import WrappedType


from .. import extractors

"""
How sip seems to handle templates:
    sip doesn't instantiate templates unless a typedef is provided for them.
    This sort of makes sense from a Python syntax point of view anyway...

    It looks like it replaces all of the template arguments's with the provided
    name. Its not obvious if non-typename template arguments are supported, but
    its not unreasonable to delay their implementation I think...
"""

class Typedef(CppType):
    def __init__(self, typedef, parent):
        super(Typedef, self).__init__(typedef, parent)
        self.platform_dependant = typedef.platformDependent

    @property
    def type(self):
        if not hasattr(self, '_type'):
            self.setup()
        return self._type

    @utils.call_once
    def setup(self):
        # Lookup the type object through TypeInfo rather through
        # self.parent.gettype because the latter won't work for basic types.
        self._type = TypeInfo(self.parent, self.item.type, self.flags).type

        # Call the types setup so it is printed before the typdef. This ensures
        # the type is printed before the typedef, allows aliasing the type in
        # Python more easily.
        self._type.setup()

        self.parent.append_to_printing_order(self)

    def print_cdef(self, pyfile):
        if self.platform_dependant:
            pyfile.write("typedef %s %s;\n" % (self.item.type, self.item.name))

    def print_pycode(self, pyfile, indent=0):
        if isinstance(self.type, WrappedType):
            pyfile.write(nci("{0.name} = {0.type.unscopedpyname}".format(self),
                            indent))

    def build_typeinfo(self, typeinfo):
        original_name = typeinfo.original
        alias_name = (
            ('const ' if typeinfo.const and not 'const ' in self.item.type else '') +
            self.item.type +
            '*' * typeinfo.ptrcount +
            ('&' if typeinfo.refcount else '')
        )

        typeinfo.flags.pyint = typeinfo.flags.pyint or self.flags.pyint
        alias_typeinfo = TypeInfo(self.parent, alias_name, typeinfo.flags)

        typeinfo.__dict__.update(alias_typeinfo.__dict__)
        typeinfo.comparison_name = alias_typeinfo.comparison_name

        if not hasattr(typeinfo, 'typedefed_type'):
            # typedefed_type should refer the non-typedef type at the bottom of
            # the chain. If typedefed_type is already set, the type bellow this
            # one in the chain is a typedef and typedefed_type already refers
            # the bottom one.
            typeinfo.typedefed_type = typeinfo.type

        typeinfo.wrapper_type = typeinfo.wrapper_type.replace(
            typeinfo.type.unscopedname, self.unscopedname)
        typeinfo.original = original_name
        typeinfo.type = self
        if self.platform_dependant:
            typeinfo.cdef_type = self.item.name

    def call_cdef_param_setup(self, typeinfo, name):
        return typeinfo.typedefed_type.call_cdef_param_setup(typeinfo, name)

    def call_cdef_param_inline(self, typeinfo, name):
        return typeinfo.typedefed_type.call_cdef_param_inline(typeinfo, name)

    def call_cdef_param_cleanup(self, typeinfo, name):
        return typeinfo.typedefed_type.call_cdef_param_cleanup(typeinfo, name)

    def virt_py_param_setup(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_py_param_setup(typeinfo, name)

    def virt_py_param_inline(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_py_param_inline(typeinfo, name)

    def virt_py_param_cleanup(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_py_param_cleanup(typeinfo, name)

    def virt_py_return(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_py_return(typeinfo, name)

    def call_cpp_param_setup(self, typeinfo, name):
        return typeinfo.typedefed_type.call_cpp_param_setup(typeinfo, name)

    def call_cpp_param_inline(self, typeinfo, name):
        ret = typeinfo.typedefed_type.call_cpp_param_inline(typeinfo, name)

        # For typedefs vary by plaform (ie time_t) we need a hard cast to the
        # original typename so that overload resolution works correctly.
        if self.platform_dependant:
            ret = "(%s)" % self.item.name + ret
        return ret

    def call_cpp_param_cleanup(self, typeinfo, name):
        return typeinfo.typedefed_type.call_cpp_param_cleanup(typeinfo, name)

    def virt_cpp_param_setup(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_cpp_param_setup(typeinfo, name)

    def virt_cpp_param_inline(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_cpp_param_inline(typeinfo, name)

    def virt_cpp_param_cleanup(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_cpp_param_cleanup(typeinfo, name)

    def virt_cpp_return(self, typeinfo, name):
        return typeinfo.typedefed_type.virt_cpp_return(typeinfo, name)

    def convert_variable_cpp_to_c(self, typeinfo, name):
        return typeinfo.typedefed_type.convert_variable_cpp_to_c(typeinfo, name)

    def convert_variable_c_to_py(self, typeinfo, name):
        return typeinfo.typedefed_type.convert_variable_c_to_py(typeinfo, name)

#----------------------------------------------------------------------------#

def generate_typedef(typedef, parent):
    Typedef(typedef, parent)
extractors.TypedefDef.generate = generate_typedef
