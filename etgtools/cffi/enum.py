from base import CppType, CppObject

from .. import extractors

def create_enum(enum, parent):
    Enum(enum, parent)
extractors.EnumDef.generate = create_enum

class Enum(CppType):
    def __init__(self, enum, parent):
        # Take enum values and put them into the parent's items list
        super(Enum, self).__init__(enum, parent)
        self.scopeprefix = parent.scopeprefix
        self.pyscopeprefix = parent.pyscopeprefix

        for val in enum.items:
            EnumValue(val, self)

class EnumValue(CppObject):
    def __init__(self, val, enum):
        super(EnumValue,self).__init__(self, enum.parent)
        enum.parent.add_object(self)
        self.type = 'const int'
