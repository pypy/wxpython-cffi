import pytest
import wrapper_lib

@wrapper_lib.abstract_class
class AbstractBase(wrapper_lib.CppWrapper):
    pass

@wrapper_lib.purevirtual_abstract_class
class PureVirtualBase(wrapper_lib.CppWrapper):
    pass

@wrapper_lib.concrete_subclass
class ConcreteSubclass(AbstractBase):
    def __init__(self):
        self.name = "concrete"

class UserSubclass(ConcreteSubclass):
    def __init__(self, i):
        self.i = i
        super(UserSubclass, self).__init__()

class UserDoubleSubclass(UserSubclass):
    def __init__(self, i):
        super(UserDoubleSubclass, self).__init__(i)
        self.i = -i

class TestAbstract(object):
    def test_abstract(self):
        with pytest.raises(TypeError):
            AbstractBase()

    def test_purevirtual(self):
        with pytest.raises(TypeError):
            PureVirtualBase()

    def test_concrete(self):
        assert ConcreteSubclass().name == "concrete"

    def test_usersubclass(self):
        obj = UserSubclass(10)
        assert obj.i == 10
        assert obj.name == "concrete"

        obj = UserDoubleSubclass(10)
        assert obj.i == -10
        assert obj.name == "concrete"
