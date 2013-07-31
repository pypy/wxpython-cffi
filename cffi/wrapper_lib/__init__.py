from cppwrapper import (
    CppWrapper, WrapperType, VirtualMethod, VirtualDispatcher,  obj_from_ptr,
    forget_ptr, take_ownership, give_ownership)
from multimethod import (
    Multimethod, StaticMultimethod, ClassMultimethod, register_type)

classname_registry = {}

def register_classname(name, cls):
    if name in classname_registry:
        raise KeyError("Class %s is already registered to '%s'" %
                       (classname_registry[name], name))
    classname_registry[name] = cls

def class_from_classname(name):
    return classname_registry[name]
