from .base import CppObject, TypeInfo

from . import utils

from .. import extractors
from ..generators import nci

# TODO: does this do anything?
class VariableBase(CppObject):
    PREFIX = ''
    def __init__(self, item, parent):
        super(VariableBase, self).__init__(item, parent)
        self.cname = self.PREFIX + self.cname

    def setup(self):
        self.type = TypeInfo(self.parent, self.item.type, self.flags)

    def print_cdef(self, pyfile):
        pyfile.write("extern {0.type.cdef_type} {0.cname};\n".format(self))

    def print_cppcode(self, cppfile):
        # TODO: Type conversion code!
        cppfile.write(nci("""\
        WL_INTERNAL {0.type.c_type} {0.cname};
        {0.type.c_type} {0.cname} = {1};
        """.format(self, self.type.convert_variable_cpp_to_c(self.name))))
        utils.pad(cppfile)

class GlobalVariable(VariableBase):
    PREFIX = 'cffigvar'

# Defines are identical to global variables except they're always ``long long``
class Define(GlobalVariable):
    PREFIX = 'cffidefine'
    def __init__(self, define, parent):
        super(Define, self).__init__(define, parent)
        self.item.type = 'const long long'

    def setup(self):
        super(Define, self).setup()

class MemberVariable(VariableBase):
    pass

#----------------------------------------------------------------------------#

def create_gvar(gvar, parent):
    GlobalVariable(gvar, parent)
extractors.GlobalVarDef.generate = create_gvar

def create_define(define, parent):
    Define(define, parent)
extractors.DefineDef.generate = create_define

def create_mvar(mvar, parent):
    MemberVariable(mvar, parent)
extractors.MemberVarDef.generate = create_mvar
