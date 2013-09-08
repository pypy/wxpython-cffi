from cppwrapper import (
    CppWrapper, WrapperType, VirtualMethod, VirtualDispatcher, abstract_class,
    concrete_subclass, purevirtual_abstract_class, obj_from_ptr, get_ptr,
    forget_ptr, take_ownership, give_ownership, keep_reference, MappedBase)
from multimethod import (
    Multimethod, StaticMultimethod, ClassMultimethod, MMTypeCheckMeta,
    check_args_types)
from lazy_defaults import LD, eval_func_defaults
from annotations import create_array_type
from deprecated import deprecated

def eval_class_attrs(cls):
    for attr in cls.__dict__.itervalues():
        eval_func_defaults(attr)
        if isinstance(attr, (Multimethod, VirtualMethod)):
            attr.finalize()

classname_registry = {}

def register_classname(name, cls):
    if name in classname_registry:
        raise KeyError("Class %s is already registered to '%s'" %
                       (classname_registry[name], name))
    classname_registry[name] = cls

def class_from_classname(name):
    return classname_registry[name]
