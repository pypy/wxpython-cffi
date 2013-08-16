import pytest

from wrapper_lib import (
    Multimethod, StaticMultimethod, ClassMultimethod, MMTypeCheckMeta)

class Seq(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

    class mm_type(object):
        __metaclass__ = MMTypeCheckMeta

        @classmethod
        def getclass(self):
            return Seq

        @classmethod
        def __instancecheck__(cls, obj):
            return (isinstance(obj, Seq) or
                    isinstance(obj, (tuple, list))
                    and len(obj) >= 2
                    and isinstance(obj[0], (int, long, float, complex))
                    and isinstance(obj[1], (int, long, float, complex)))

        @staticmethod
        def convert(obj):
            if isinstance(obj, Seq):
                return obj
            return Seq(obj[0], obj[1])

class Number(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    class mm_type(object):
        __metaclass__ = MMTypeCheckMeta

        @classmethod
        def getclass(self):
            return Number

        @classmethod
        def __instancecheck__(cls, obj):
            return isinstance(obj, (int, long, float, complex, Number))

        @staticmethod
        def convert(obj):
            if isinstance(obj, Number):
                return obj
            return Number(obj)

class ClassWithMMs(object):
    builtin_types = Multimethod()

    @builtin_types.overload()
    def builtin_types(self):
        return tuple()

    @builtin_types.overload(i=int)
    def builtin_types(self, i):
        return (i,)

    @builtin_types.overload(i=int, l=list)
    def builtin_types(self, i, l):
        return (i, l)

    @builtin_types.overload(one=tuple, two=tuple)
    def builtin_types(self, one, two=(2, 3)):
        return one + two

    @builtin_types.overload(f=float, k=tuple)
    def builtin_types(self, f, k=(1, 2, 3)):
        return (f, k)

    instance_mm = Multimethod()

    @instance_mm.overload()
    def instance_mm(self):
        return (self,)

    @instance_mm.overload(d=dict)
    def instance_mm(self, d):
        return (self, d)

    @instance_mm.overload(i=int, n=int)
    def instance_mm(self, i, n=10):
        return (self, i, n)

    class_mm = ClassMultimethod()

    @class_mm.overload()
    def class_mm(cls):
        return (cls,)

    @class_mm.overload(d=dict)
    def class_mm(cls, d):
        return (cls, d)

    @class_mm.overload(i=int, n=int)
    def class_mm(cls, i=9, n=10):
        return (cls, i, n)

    static_mm = StaticMultimethod()

    @static_mm.overload()
    def static_mm():
        return tuple()

    @static_mm.overload(d=dict)
    def static_mm(d):
        return (d,)

    @static_mm.overload(i=int, n=int)
    def static_mm(i=9, n=10):
        return (i, n)

    usertypes = Multimethod()

    @usertypes.overload()
    def usertypes(self):
        return tuple()

    @usertypes.overload(seq=Seq.mm_type)
    def usertypes(self, seq):
        seq = Seq.mm_type.convert(seq)
        return (seq.x, seq.y)

    @usertypes.overload(numb=Number.mm_type)
    def usertypes(self, numb):
        numb = Number.mm_type.convert(numb)
        return (numb,)

    delayed = Multimethod()

    @delayed.overload(i='int')
    def delayed(self, i):
        return i * 2

    @delayed.overload(i='SomeClass')
    def delayed(self, i):
        return i.i / 2

class SomeClass(object):
    def __init__(self, i):
        self.i = i

ClassWithMMs.delayed.finalize(globals())


class TestMultimethods(object):
    def test_positional(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.builtin_types() == tuple()
        assert mm_obj.builtin_types(42) == (42,)
        assert mm_obj.builtin_types(-1, [1]) == (-1, [1])
        assert mm_obj.builtin_types(l=[1], i=-1) == (-1, [1])

        assert mm_obj.builtin_types((0,)) == (0, 2, 3)
        assert mm_obj.builtin_types((2,), (1,)) == (2, 1)
        assert mm_obj.builtin_types((2,), two=(1,)) == (2, 1)
        assert mm_obj.builtin_types(one=(2,), two=(1,)) == (2, 1)
        assert mm_obj.builtin_types(two=(2,), one=(1,)) == (1, 2)

        assert mm_obj.builtin_types(2.0) == (2.0, (1, 2, 3))
        assert mm_obj.builtin_types(k=(0, 1), f=0.2) == (0.2, (0, 1))

        with pytest.raises(TypeError):
            mm_obj.builtin_types("foo")

        with pytest.raises(TypeError):
            mm_obj.builtin_types((1,), (2,), (3,))

        with pytest.raises(TypeError):
            mm_obj.builtin_types((1, 2), 0.1)

    def test_instace_methods(self):
        mm_cls = ClassWithMMs
        mm_obj = ClassWithMMs()
        assert mm_obj.instance_mm() == (mm_obj,)
        assert mm_obj.instance_mm({1: 10}) == (mm_obj, {1: 10})
        assert mm_obj.instance_mm(n=2, i=3) == (mm_obj, 3, 2)

        assert mm_obj.instance_mm() == mm_cls.instance_mm(mm_obj)
        assert (mm_obj.instance_mm({1: 10}) ==
                mm_cls.instance_mm(mm_obj, {1: 10}))
        assert (mm_obj.instance_mm(n=2, i=3) ==
                mm_cls.instance_mm(mm_obj, n=2, i=3))

    def test_class_methods(self):
        mm_cls = ClassWithMMs
        mm_obj = ClassWithMMs()
        assert mm_obj.class_mm() == mm_cls.class_mm()
        assert mm_obj.class_mm({1: 10}) == mm_obj.class_mm({1: 10})
        assert mm_obj.class_mm(n=2, i=3) == mm_obj.class_mm(n=2, i=3)

    def test_static_methods(self):
        mm_cls = ClassWithMMs
        mm_obj = ClassWithMMs()
        assert mm_obj.static_mm() == mm_cls.static_mm()
        assert mm_obj.static_mm({1: 10}) == mm_obj.static_mm({1: 10})
        assert mm_obj.static_mm(n=2, i=3) == mm_obj.static_mm(n=2, i=3)

    def test_usertypes(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.usertypes() == tuple()
        assert mm_obj.usertypes(10) == (Number(10),)
        assert mm_obj.usertypes(Number(10)) == (Number(10),)
        assert mm_obj.usertypes([2, 4]) == (2, 4)
        assert mm_obj.usertypes(Seq(2, 4)) == (2, 4)

    def test_delayedtypes(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.delayed(14) == 28
        assert mm_obj.delayed(SomeClass(24)) == 12
