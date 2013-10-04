from .base import CppType, CppObject

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

#TODO: maybe it makes more sense to move this into varable.py?
class EnumValue(CppObject):
    def __init__(self, val, parent):
        super(EnumValue,self).__init__(val, parent)
        self.type = 'const int'
