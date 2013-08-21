from cppwrapper import CppWrapper, MappedBase, ffi, get_ptr
import collections

#----------------------------------------------------------------------------#
# Array

class SeqType(type):
    def __instancecheck__(self, seq):
        if not isinstance(seq, collections.Sequence):
            return False

        for obj in seq:
            if not isinstance(obj, self._cls):
                return False
        return True

class CppWrapperSeq(object):
    __metaclass__ = SeqType

    @classmethod
    def py2c(self, seq):
        seq_len = len(seq)
        array = self._array_func(seq_len)
        for i in range(seq_len):
            assign_func(array, i, get_ptr(seq[i]))

        return array, array_len, None

    @classmethod
    def c2py(self, array, len):
        raise NotImplementedError()

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

def create_array_type(cls, ctype=None, array_func=None, assign_func=None):
    if cls in seq_type_cache:
        return seq_type_cache[cls]

    if issubclass(cls, MappedBase):
        class Seq(MappedTypeSeq):
            _cls = cls
            _array_ctype = ctype + '[]'
        seq_type_cache[cls] = Seq
        return Seq

    elif issubclass(cls, CppWrapper):
        class Seq(CppWrapperSeq):
            _cls = cls
            _array_func = array_func
            _assign_func = assign_func
        seq_type_cache[cls] = Seq
        return Seq
