import collections

class MappedType(type):
    def __new__(cls, name, bases, attrs):
        if len(bases) == 1 and (bases[0] == object or bases[0] == MappedBase):
            return super(MappedType, cls).__new__(cls, name, bases, attrs)
        raise TypeError()

    def __instancecheck__(self, instance):
        return self.__instancecheck__(instance)

class MappedBase(object):
    __metaclass__ = MappedType

    def __init__(self, *args, **kwargs):
        raise TypeError()

def create_mapped_type_seq(cls, ctype, ffi):
    array_ctype = ctype + '[]'
    class MappedTypeSeq(MappedBase):
        @staticmethod
        def __instancecheck__(seq):
            if not isinstance(seq, collections.Sequence):
                raise TypeError()

            for obj in seq:
                if not isinstance(obj, cls):
                    raise TypeError()
            return True

        @staticmethod
        def py2c(seq):
            def test(cdata):
                print ffi.string(cdata)
            keepalive = [cls.py2c(obj) for obj in seq]
            array = ffi.new(array_ctype, keepalive)
            return array, keepalive

        @staticmethod
        def c2py(array, len):
            return [cls.c2py(array[i]) for i in range(len)]

    return MappedTypeSeq
