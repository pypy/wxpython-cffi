import gc
import cffi
import pytest
import weakref
from os import path

from wrapper_lib import (
    CppWrapper, wrapper_class, virtual_method, object_registry)

ffi = cffi.FFI()
ffi.cdef('''
int deleted_count;
int call_virtual_meth(void *obj, int i);

void (*DtorObj_vtable[2])();
void* DtorObj_88__op_new();
void DtorObj_88__op_delete(void *self);
int DtorObj_88_non_virtual_meth(void *self, int i);
int DtorObj_88_virtual_meth(void *self, int i);

void* NoDtorObj_88__op_new();
void NoDtorObj_88__op_delete(void *obj);
''')

clib = ffi.verify('''
extern int deleted_count;
int call_virtual_meth(void *obj, int i);

extern void (*DtorObj_vtable[2])();
void* DtorObj_88__op_new();
void DtorObj_88__op_delete(void *self);
int DtorObj_88_non_virtual_meth(void *self, int i);
int DtorObj_88_virtual_meth(void *self, int i);

void* NoDtorObj_88__op_new();
void NoDtorObj_88__op_delete(void *obj);
''', sources=[path.join(path.dirname(__file__), 'test_cppwrapper.cpp')])


def collect_all_wrappers():
    while True:
        deleted_count = clib.deleted_count
        gc.collect()
        if deleted_count == clib.deleted_count:
            break


class NoDtorObj(CppWrapper):
    __metaclass__ = wrapper_class(ffi, clib)

    def __init__(self):
        cpp_obj = clib.NoDtorObj_88__op_new()
        CppWrapper.__init__(self, cpp_obj)

    def __del__(self):
        clib.NoDtorObj_88__op_delete(self._cpp_obj)

METHIDX_DtorObj_88_virtual_meth = 1
DtorObj_vtable = [
    "",
    "int(*)(void*, int)"
]

class DtorObj(CppWrapper):
    __metaclass__ = wrapper_class(ffi, clib, clib.DtorObj_vtable,
                                  DtorObj_vtable)

    def __init__(self):
        cpp_obj = clib.DtorObj_88__op_new()
        CppWrapper.__init__(self, cpp_obj)

    def __del__(self):
        clib.DtorObj_88__op_delete(self._cpp_obj)

    def non_virtual_meth(self, i):
        return clib.DtorObj_88_non_virtual_meth(self._cpp_obj, i)

    def virtual_meth(self, i):
        return clib.DtorObj_88_virtual_meth(self._cpp_obj, i)

    @virtual_method(METHIDX_DtorObj_88_virtual_meth)
    def _virtual_virtul_meth(ptr, i):
        self = object_registry.obj_from_ptr(ptr, DtorObj)
        return self.virtual_meth(i)

    #def call_dtor(self):
        #clib.DtorObj_88__op_delete(

class TestMethodCalls(object):
    def test_nonvirtual_method(self):
        obj = DtorObj()
        assert obj.non_virtual_meth(10) == 10

    def test_virtual_method(self):
        obj = DtorObj()
        assert obj.virtual_meth(10) == 10

    def test_overridden_virtual_method(self):
        def override(i):
            return -i

        obj = DtorObj()
        obj.virtual_meth = override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

class TestCppObjectLifetimes(object):
    def test_cpp_owned_no_dtor(self):
        collect_all_wrappers()
        deleted_count = clib.deleted_count
        obj = NoDtorObj()
        object_registry.give_ownership(obj)
        del obj
        collect_all_wrappers()

        assert deleted_count == clib.deleted_count

    def test_cpp_owned_dtor(self):
        collect_all_wrappers()
        deleted_count = clib.deleted_count
        obj = DtorObj()
        object_registry.give_ownership(obj)
        del obj
        collect_all_wrappers()

        assert deleted_count + 1 == clib.deleted_count

    def test_py_owned(self):
        collect_all_wrappers()
        deleted_count = clib.deleted_count
        NoDtorObj()
        collect_all_wrappers()

        assert deleted_count + 1 == clib.deleted_count

class TestPyObjectLifetimes(object):
    def test_no_parent_py_owned(self):
        obj = NoDtorObj()
        wk = weakref.ref(obj)
        del obj
        collect_all_wrappers()

        assert wk() is None

    def test_no_parent_cpp_owned(self):
        obj = DtorObj()
        wk = weakref.ref(obj)
        object_registry.give_ownership(obj, None)

        del obj
        collect_all_wrappers()
        assert wk() is not None

        wk().__del__
        collect_all_wrappers()
        assert wk() is None

    def test_py_owned_parent_dies(self):
        # Only test C++ owned child objects; Python owned objects don't have
        # parents
        parent = NoDtorObj()
        child = NoDtorObj()
        object_registry.give_ownership(child, parent)

        pwk = weakref.ref(parent)
        cwk = weakref.ref(child)
        del child
        del parent
        collect_all_wrappers()

        assert pwk() is None
        assert cwk() is None

    def test_cpp_owned_parent_dies(self):
        parent = DtorObj()
        child = NoDtorObj()

        object_registry.give_ownership(parent, None)
        object_registry.give_ownership(child, parent)

        pwk = weakref.ref(parent)
        cwk = weakref.ref(child)
        del child
        del parent
        collect_all_wrappers()

        assert pwk() is not None
        assert cwk() is not None

        pwk().__del__()
        collect_all_wrappers()
        assert pwk() is None
        assert cwk() is None

    def test_multiple_children(self):
        parent = DtorObj()
        child1 = NoDtorObj()
        child2 = NoDtorObj()

        object_registry.give_ownership(parent, None)
        object_registry.give_ownership(child1, parent)
        object_registry.give_ownership(child2, parent)

        pwk = weakref.ref(parent)
        cwk1 = weakref.ref(child1)
        cwk2 = weakref.ref(child2)
        del child1
        del child2
        del parent
        collect_all_wrappers()

        assert pwk() is not None
        assert cwk1() is not None
        assert cwk2() is not None

        pwk().__del__()
        collect_all_wrappers()
        assert pwk() is None
        assert cwk1() is None
        assert cwk2() is None

class TestObjectLookup(object):
    pass
