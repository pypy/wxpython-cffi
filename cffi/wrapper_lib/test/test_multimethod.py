import pytest

from wrapper_lib import Multimethod

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

class TestMultimethods(object):
    def setup_class(self):
        self.mm_obj = ClassWithMMs()

    def test_positional(self):
        assert self.mm_obj.positional_builtins() == tuple()
        assert self.mm_obj.positional_builtins(42) == (42,)
        assert self.mm_obj.positional_builtins(-1, [1]) == (-1, [1])

        with pytest.raises(TypeError):
            self.mm_obj.positional_builtins("foo")

    def test_keyword(self):
        assert self.mm_obj.keyword_builtins(l=[-1, 4]) == (10, [-1, 4])
        assert self.mm_obj.keyword_builtins(i=99) == (99, [1, 2, 3])
        assert self.mm_obj.keyword_builtins(i=99, l=[-1, 4]) == (99, [-1, 4])

        assert self.mm_obj.keyword_builtins(l=(-1, 4)) == (0.2, (-1, 4))
        assert self.mm_obj.keyword_builtins(i=3.1) == (3.1, (1, 2, 3))
        assert self.mm_obj.keyword_builtins(i=3.1, l=(-1, 4)) == (3.1, (-1, 4))

    def test_mixed(self):
        assert self.mm_obj.mixed_builtins(0) == (0, [1, 2, 3])
        assert self.mm_obj.mixed_builtins(0, []) == (0, [])

        assert self.mm_obj.mixed_builtins(0) == (0, [1, 2, 3])
        assert self.mm_obj.mixed_builtins(0, []) == (0, [])

        assert self.mm_obj.mixed_builtins() == (1, 2, 2, 3)
        assert self.mm_obj.mixed_builtins((0,)) == (0, 2, 3)
        assert self.mm_obj.mixed_builtins((2,), (1,)) == (2, 1)
        assert self.mm_obj.mixed_builtins((2,), two=(1,)) == (2, 1)
        assert self.mm_obj.mixed_builtins(one=(2,), two=(1,)) == (2, 1)
        assert self.mm_obj.mixed_builtins(two=(2,), one=(1,)) == (1, 2)
