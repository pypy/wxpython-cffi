import __builtin__
import warnings
from cppwrapper import ffi

exception_registry = { }

EXCEPTION_NAME = ffi.new('char**')
EXCEPTION_STRING = ffi.new('char**')

def register_exception(e):
    exception_registry[e.__name__] = e

def check_exception(clib):
    if EXCEPTION_NAME[0] == ffi.NULL:
        return

    if EXCEPTION_STRING[0] == ffi.NULL:
        warnings.warn('exception name is set, but exception string is unset')
        return

    e_name = ffi.string(EXCEPTION_NAME[0])
    e_string = ffi.string(EXCEPTION_STRING[0])

    clib.free(EXCEPTION_NAME[0])
    clib.free(EXCEPTION_STRING[0])

    EXCEPTION_NAME[0] = ffi.NULL
    EXCEPTION_STRING[0] = ffi.NULL

    if e_name in exception_registry:
        raise exception_registry[e_name](e_string)
    else:
        raise getattr(__builtin__, e_name, Exception)(e_string)
