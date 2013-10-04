from .base import CppObject

from .. import extractors

# TODO: does this do anything?
class VariableBase(CppObject):
    def __init__(self, item, parent):
        super(VariableBase, self).__init__(item, parent)

class GlobalVariable(VariableBase):
    pass

# Defines are identical to global variables except they're always ``long long``
class Define(GlobalVariable):
    def __init__(self, define, parent):
        super(Define, self).__init__(define, parent)
        self.type = 'const long long'

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
