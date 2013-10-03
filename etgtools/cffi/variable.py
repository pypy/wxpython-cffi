from base import CppObject

from .. import extractors

# TODO: does this do anything?
class VariableBase(CppObject):
    def __init__(self, item, parent):
        super(VariableBase, self).__init__(item, parent)


def create_gvar(gvar, parent):
    GlobalVariable(gvar, parent)
extractors.GlobalVariableDef.generate = create_gvar
class GlobalVariable(VariableBase):
    pass

# Defines are identical to global variables except they're always ``long long``
def create_define(define, parent):
    Define(define, parent)
extractors.DefineDef.generate = create_define
class Define(GlobalVariable):
    def __init__(self, define)
        super(Define, self).__init__(define, parent)
        self.type = 'const long long'

def create_mvar(mvar, parent):
    MemberVariable(mvar, parent)
extractors.MemberVariableDef.generate = create_mvar
class MemberVariable(VariableBase):
    pass
