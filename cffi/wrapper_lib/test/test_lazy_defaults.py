from wrapper_lib import LD, eval_func_defaults, eval_class_attrs

def lazy_default_func(i, j=LD('some_global_int')):
    return i * j

class LazyDefaultClass(object):
    def __init__(self, i):
        self.i = i

    def lazy_default_method(self, j=LD('some_other_global_int')):
        return self.i * j

some_global_int = 100
some_other_global_int = 101

eval_func_defaults(lazy_default_func)
eval_class_attrs(LazyDefaultClass)

class TestLazyDefaults(object):
    def test_func_lazy_defaults(self):
        assert lazy_default_func(2) == 200
        assert lazy_default_func(2, 2) == 4

    def test_method_lazy_defaults(self):
        obj = LazyDefaultClass(3)
        assert obj.lazy_default_method() == 303
        assert obj.lazy_default_method(9) == 27
