import pytest

from wrapper_lib import (
    Multimethod, StaticMultimethod, ClassMultimethod, register_type)

class Seq(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y

def check_Seq(obj, type):
    return (isinstance(obj, (tuple, list))
            and len(obj) >= 2
            and isinstance(obj[0], (int, long, float, complex))
            and isinstance(obj[1], (int, long, float, complex))
            or isinstance(obj, Seq))

def convert_Seq(obj):
    if isinstance(obj, Seq):
        return obj
    return Seq(obj[0], obj[1])

register_type(Seq, check_Seq, convert_Seq)

class Number(object):
    def __init__(self, value):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

def check_Number(obj, type):
    return isinstance(obj, (int, long, float, complex, Number))

register_type(Number, check_Number)

class ClassWithMMs(object):
    positional_builtins = Multimethod()

    @positional_builtins.overload()
    def positional_builtins(self):
        return tuple()

    @positional_builtins.overload(int)
    def positional_builtins(self, i):
        return (i,)

    @positional_builtins.overload(int, list)
    def positional_builtins(self, i, l):
        return (i, l)


    keyword_builtins = Multimethod()

    @keyword_builtins.overload(i=int, l=list)
    def keyword_builtins(self, i=10, l=[1, 2, 3]):
        return (i, l)

    @keyword_builtins.overload(i=float, l=tuple)
    def keyword_builtins(self, i=0.2, l=(1, 2, 3)):
        return (i, l)


    mixed_builtins = Multimethod()

    @mixed_builtins.overload(int, l=list)
    def mixed_builtins(self, i, l=[1, 2, 3]):
        return (i, l)

    @mixed_builtins.overload(float, l=tuple)
    def mixed_builtins(self, f, l=(1, 2, 3)):
        return (f, l)

    @mixed_builtins.overload("one", "two", one=tuple, two=tuple)
    def mixed_builtins(self, one=(1, 2), two=(2, 3)):
        return one + two

    instance_builtins = Multimethod()

    @instance_builtins.overload()
    def instance_builtins(self):
        return (self,)

    @instance_builtins.overload(dict)
    def instance_builtins(self, d):
        return (self, d)

    @instance_builtins.overload(i=int, n=int)
    def instance_builtins(self, i=9, n=10):
        return (self, i, n)

    class_builtins = ClassMultimethod()

    @class_builtins.overload()
    def class_builtins(cls):
        return (cls,)

    @class_builtins.overload(dict)
    def class_builtins(cls, d):
        return (cls, d)

    @class_builtins.overload(i=int, n=int)
    def class_builtins(cls, i=9, n=10):
        return (cls, i, n)

    static_builtins = StaticMultimethod()

    @static_builtins.overload()
    def static_builtins():
        return tuple()

    @static_builtins.overload(dict)
    def static_builtins(d):
        return (d,)

    @static_builtins.overload(i=int, n=int)
    def static_builtins(i=9, n=10):
        return (i, n)

    usertypes = Multimethod()

    @usertypes.overload()
    def usertypes(self):
        return tuple()

    @usertypes.overload(Seq)
    def usertypes(self, seq):
        return (seq.x, seq.y)

    @usertypes.overload(Number)
    def usrtypes(self, numb):
        return (numb,)


class TestMultimethods(object):
    def test_positional(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.positional_builtins() == tuple()
        assert mm_obj.positional_builtins(42) == (42,)
        assert mm_obj.positional_builtins(-1, [1]) == (-1, [1])

        with pytest.raises(TypeError):
            mm_obj.positional_builtins("foo")

    def test_keyword(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.keyword_builtins(l=[-1, 4]) == (10, [-1, 4])
        assert mm_obj.keyword_builtins(i=99) == (99, [1, 2, 3])
        assert mm_obj.keyword_builtins(i=99, l=[-1, 4]) == (99, [-1, 4])

        assert mm_obj.keyword_builtins(l=(-1, 4)) == (0.2, (-1, 4))
        assert mm_obj.keyword_builtins(i=3.1) == (3.1, (1, 2, 3))
        assert mm_obj.keyword_builtins(i=3.1, l=(-1, 4)) == (3.1, (-1, 4))

    def test_mixed(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.mixed_builtins(0) == (0, [1, 2, 3])
        assert mm_obj.mixed_builtins(0, l=[]) == (0, [])
        with pytest.raises(TypeError):
            mm_obj.mixed_builtins(0, [])

        assert mm_obj.mixed_builtins(.7) == (.7, (1, 2, 3))
        assert mm_obj.mixed_builtins(.7, l=tuple()) == (.7, tuple())

        assert mm_obj.mixed_builtins() == (1, 2, 2, 3)
        assert mm_obj.mixed_builtins((0,)) == (0, 2, 3)
        assert mm_obj.mixed_builtins((2,), (1,)) == (2, 1)
        assert mm_obj.mixed_builtins((2,), two=(1,)) == (2, 1)
        assert mm_obj.mixed_builtins(one=(2,), two=(1,)) == (2, 1)
        assert mm_obj.mixed_builtins(two=(2,), one=(1,)) == (1, 2)

    def test_instace_methods(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.instance_builtins() == (mm_obj,)
        assert mm_obj.instance_builtins({1: 10}) == (mm_obj, {1: 10})
        assert mm_obj.instance_builtins(n=2, i=3) == (mm_obj, 3, 2)

    def test_class_methods(self):
        mm_cls = ClassWithMMs
        mm_obj = ClassWithMMs()
        assert mm_obj.class_builtins() == mm_cls.class_builtins()
        assert mm_obj.class_builtins({1: 10}) == mm_obj.class_builtins({1: 10})
        assert mm_obj.class_builtins(n=2, i=3) == mm_obj.class_builtins(n=2, i=3)

    def test_static_methods(self):
        mm_cls = ClassWithMMs
        mm_obj = ClassWithMMs()
        assert mm_obj.static_builtins() == mm_cls.static_builtins()
        assert mm_obj.static_builtins({1: 10}) == mm_obj.static_builtins({1: 10})
        assert mm_obj.static_builtins(n=2, i=3) == mm_obj.static_builtins(n=2, i=3)

    def test_usertypes(self):
        mm_obj = ClassWithMMs()
        assert mm_obj.usertypes() == tuple()
        assert mm_obj.usertypes(10) == (Number(10),)
        assert mm_obj.usertypes(Number(10)) == (Number(10),)
        assert mm_obj.usertypes([2, 4]) == (2, 4)
        assert mm_obj.usertypes(Seq(2, 4)) == (2, 4)
