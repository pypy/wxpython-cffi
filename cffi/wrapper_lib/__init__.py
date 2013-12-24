from cppwrapper import (
    CppWrapper, WrapperType, VirtualMethod, VirtualMethodStub,
    VirtualDispatcher, register_cpp_classname, obj_from_ptr, get_ptr,
    forget_ptr, take_ownership, give_ownership, keep_reference, MappedBase,
    instancecheck, convert_to_type)
from multimethod import (
    Multimethod, StaticMultimethod, ClassMultimethod, MMTypeCheckMeta,
    check_args_types)
from lazy_defaults import LD, eval_func_defaults
from annotations import create_array_type, allocate_cstring, allocate_cunicode
from deprecated import deprecated
from exceptions import register_exception, check_exception
from refcounting import adjust_refcount, get_refcounted_handle
from abstract import (
    abstract_class, concrete_subclass, purevirtual_abstract_class)
from voidptr import VoidPtrABC
from defaults import default_arg_indicator

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

def populate_clib_ptrs(clib):
    # Each module contains function pointers (declared in include/wrapper_lib.h)
    # which need to populated before C code from the module is run.
    clib.WL_ADJUST_REFCOUNT = refcounting.adjust_refcount_cb
    clib.WL_EXCEPTION_NAME = exceptions.EXCEPTION_NAME
    clib.WL_EXCEPTION_STRING = exceptions.EXCEPTION_STRING
