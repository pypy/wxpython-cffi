from .base import CppType, CppObject, TypeInfo
from .variable import VariableBase

from .. import extractors

def create_enum(enum, parent):
    Enum(enum, parent)
extractors.EnumDef.generate = create_enum

class Enum(CppType):
    def __init__(self, enum, parent):
        # Take enum values and put them into the parent scope
        super(Enum, self).__init__(enum, parent)

        for val in enum.items:
            EnumValue(val, parent)

    def gettypeinfo(self, original, name, flags):
        pass

#TODO: maybe it makes more sense to move this into varable.py?
class EnumValue(VariableBase):
    PREFIX = 'cffienumval'
    def __init__(self, val, parent):
        super(EnumValue,self).__init__(val, parent)
        self.type = 'const int'

    def setup(self):
        self.type = TypeInfo(self.parent, self.type, self.flags)
