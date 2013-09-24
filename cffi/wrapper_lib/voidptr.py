from multimethod import MMTypeCheckMeta
from _ffi import ffi

class VoidPtrABC(object):
    __metaclass__ = MMTypeCheckMeta

    @classmethod
    def __instancecheck__(cls, obj):
        try:
            ffi.cast('void*', obj)
            return True
        except TypeError:
            return False
