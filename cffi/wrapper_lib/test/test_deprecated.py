import pytest
import wrapper_lib

@wrapper_lib.deprecated
def deprecated_func():
    pass

class ClassWithDeprecatedMethod(object):
    @wrapper_lib.deprecated('ClassWithDeprecatedMethod')
    def __init__(self):
        pass

    @wrapper_lib.deprecated('ClassWithDeprecatedMethod')
    def deprecated_method(self):
        assert isinstance(self, ClassWithDeprecatedMethod)

    @classmethod
    @wrapper_lib.deprecated('ClassWithDeprecatedMethod')
    def deprecated_classmethod(cls):
        assert cls is ClassWithDeprecatedMethod

    @staticmethod
    @wrapper_lib.deprecated('ClassWithDeprecatedMethod')
    def deprecated_staticmethod():
        pass

    @wrapper_lib.Multimethod
    def deprecated_multimethod(self):
        pass

    @deprecated_multimethod.deprecated_overload('ClassWithDeprecatedMethod')
    def deprecated_multimethod(self):
        assert isinstance(self, ClassWithDeprecatedMethod)

@wrapper_lib.Multimethod
def deprecated_multimethod():
    pass

@deprecated_multimethod.deprecated_overload()
def deprecated_multimethod():
    pass

class TestDeprecated(object):
    def test_function(self):
        pytest.deprecated_call(deprecated_func)
        pytest.deprecated_call(deprecated_multimethod)

    def test_methods(self):
        obj = pytest.deprecated_call(ClassWithDeprecatedMethod)
        pytest.deprecated_call(obj.deprecated_method)
        pytest.deprecated_call(obj.deprecated_classmethod)
        pytest.deprecated_call(obj.deprecated_staticmethod)
        pytest.deprecated_call(obj.deprecated_multimethod)
