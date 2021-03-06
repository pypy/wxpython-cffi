from cppwrapper import (
    CppWrapper, WrapperType, VirtualMethod, VirtualMethodStub,
    VirtualDispatcher, register_cpp_classname, obj_from_ptr, get_ptr,
    forget_ptr, take_ownership, give_ownership, keep_reference, MappedBase,
    is_alive,
    instancecheck, convert_to_type, init_wrapper, hassubclass, CastData)
from multimethod import (
    MMTypeCheckMeta, MMTypeError, MMInternalError, check_arg_type,
    check_args_types, raise_mm_arg_failure)
from annotations import create_array_type, allocate_cstring, allocate_cunicode
from deprecated import deprecated_msg
from exceptions import register_exception, check_exception
from refcounting import adjust_refcount, get_refcounted_handle
from abstract import (
    abstract_class, concrete_subclass, purevirtual_abstract_class)
from voidptr import VoidPtrABC
from defaults import default_arg_indicator

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
