from .base import CppType, TypeInfo, ItemFlags

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

    def setup(self):
        # Lookup the type object through TypeInfo rather through
        # self.parent.gettype because the latter won't work for basic types.
        self.type = TypeInfo(self.parent, self.item.type, self.flags).type

    def print_cdef(self, pyfile):
        pyfile.write("typedef %s %s;\n" % (self.item.type, self.item.name))

    def build_typeinfo(self, typeinfo):
        self.type.build_typeinfo(typeinfo)

        typeinfo.type = self
        if self.platform_dependant:
            typeinfo.cdef_type = self.item.name

    def call_cpp_param_inline(self, typeinfo, name):
        ret = self.type.call_cpp_param_inline(typeinfo, name)

        # For typedefs vary by plaform (ie time_t) we need a hard cast to the
        # original typename so that overload resolution works correctly.
        if self.platform_dependant:
            ret = "(%s)" % self.item.name + name
        return ret

    def __getattr__(self, attr):
        # TODO: Fix this. It actually should probably use __getattribute__ to
        #       delegate anything not in __dict__ to self.type
        #       Alternatively, just copy the methods onto self from self.type?
        return getattr(self.type, attr)

#----------------------------------------------------------------------------#

def generate_typedef(typedef, parent):
    Typedef(typedef, parent)
extractors.TypedefDef.generate = generate_typedef
