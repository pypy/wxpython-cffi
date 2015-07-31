from .base import CppObject, TypeInfo
from .function import Method

from . import utils

from .. import extractors
from ..generators import nci

class VariableBase(CppObject):
    PREFIX = ''
    def __init__(self, item, parent):
        super(VariableBase, self).__init__(item, parent)
        self.cname = self.PREFIX + self.cname

    def setup(self):
        self.type = TypeInfo(self.parent, self.item.type, self.flags)

    def print_cdef_and_verify(self, pyfile):
        pyfile.write("extern {0.type.cdef_type} {0.cname};\n".format(self))

    def print_cppcode(self, cppfile):
        cppfile.write(nci("""\
        WL_INTERNAL {0.type.c_type} {0.cname};
        {0.type.c_type} {0.cname} = {1};
        """.format(self, self.type.convert_variable_cpp_to_c(self.unscopedname))))
        utils.pad(cppfile)

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci(
            "{0} = {1}".format(self.pyname,
                               self.type.convert_variable_c_to_py("clib." + self.cname)),
            indent))

class GlobalVariable(VariableBase):
    PREFIX = 'cffigvar'

# Defines are identical to global variables except they're always ``int``
class Define(GlobalVariable):
    PREFIX = 'cffidefine'
    def __init__(self, define, parent):
        super(Define, self).__init__(define, parent)
        self.type = 'const int'

    def setup(self):
        self.type = TypeInfo(self.parent, self.type, self.flags)

#----------------------------------------------------------------------------#

def create_gvar(gvar, parent):
    GlobalVariable(gvar, parent)
extractors.GlobalVarDef.generate = create_gvar

def create_define(define, parent):
    Define(define, parent)
extractors.DefineDef.generate = create_define
