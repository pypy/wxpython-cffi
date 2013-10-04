from .base import CppType

from .. import extractors

def create_mappedtype(mtype, parent):
    MappedType(mtype, parent)
extractors.MappedTypeDef_cffi.generate = create_mappedtype

class MappedType(CppType):
    def __init__(self, cls, parent):
        super(MappedType, self).__init__(cls, parent)
