import __builtin__
import warnings
from cppwrapper import ffi

exception_registry = { }

def register_exception(e):
    exception_registry[e.__name__] = e

def check_exception(clib):
    if clib.cffiexception_name == ffi.NULL:
        return

    if clib.cffiexception_string == ffi.NULL:
        warnings.warn('exception name is set, but exception string is unset')
        return

    e_name = ffi.string(clib.cffiexception_name)
    e_string = ffi.string(clib.cffiexception_string)

    clib.free(clib.cffiexception_name)
    clib.free(clib.cffiexception_string)

    clib.cffiexception_name = ffi.NULL
    clib.cffiexception_string = ffi.NULL

    if e_name in exception_registry:
        raise exception_registry[e_name](e_string)
    else:
        raise getattr(__builtin__, e_name, Exception)(e_string)
