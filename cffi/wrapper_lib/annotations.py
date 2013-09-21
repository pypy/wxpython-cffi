import collections

from _ffi import ffi
from cppwrapper import CppWrapper, MappedBase, get_ptr, obj_from_ptr


#----------------------------------------------------------------------------#
# Array

class SeqType(type):
    def __instancecheck__(self, seq):
        if not isinstance(seq, collections.Sequence):
            return False

        if hasattr(self._cls, '_pyobject_mapping_'):
            type = (self._cls, self._cls._pyobject_mapping)
        else:
            type = self._cls
        for obj in seq:
            if not isinstance(obj, type):
                return False
        return True

class CppWrapperSeq(object):
    __metaclass__ = SeqType

    @classmethod
    def py2c(self, seq):
        seq_len = len(seq)
        array = ffi.new('void*[]', seq_len)
        keepalive = []
        for i in range(seq_len):
            if isinstance(seq[i], self._cls):
                array[i] = get_ptr(seq[i])
            else:
                obj = self._cls._pyobject_mapping_.convert(seq[i])
                keepalive.append(obj)
                array[i] = get_ptr(obj)

        return array, seq_len, (array, keepalive)

    @classmethod
    def c2py(self, array, len):
        return [obj_from_ptr(array[i], self._cls) for i in range(len)]

class MappedTypeSeq(object):
    __metaclass__ = SeqType

    @classmethod
    def py2c(self, seq):
        def test(cdata):
            print ffi.string(cdata)
        for obj in seq:
            keepalive = [self._cls.py2c(obj) for obj in seq]
        array = ffi.new(self._array_ctype, [i[0] for i in keepalive])
        return array, len(seq), keepalive

    @classmethod
    def c2py(self, array, len):
        return [self._cls.c2py(array[i]) for i in range(len)]

seq_type_cache = {}

def create_array_type(cls, ctype=None):
    if cls in seq_type_cache:
        return seq_type_cache[cls]

    if issubclass(cls, MappedBase):
        class Seq(MappedTypeSeq):
            _cls = cls
            _array_ctype = ctype
        seq_type_cache[cls] = Seq

    elif issubclass(cls, CppWrapper):
        class Seq(CppWrapperSeq):
            _cls = cls
        seq_type_cache[cls] = Seq
    return Seq

#----------------------------------------------------------------------------#
# C Strings

def allocate_cstring(str, clib):
    cstring = ffi.cast('char*', clib.malloc(len(str) + 1))
    for i, c in enumerate(str):
        cstring[i] = c
    cstring[i + 1] = '\0'

    return cstring
