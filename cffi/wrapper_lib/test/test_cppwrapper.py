import gc
import cffi
import pytest
import weakref
from os import path

from wrapper_lib import (
    CppWrapper, VirtualMethod, VirtualDispatcher, obj_from_ptr,
    forget_ptr, take_ownership, give_ownership)

ffi = cffi.FFI()
ffi.cdef('''
int deleted_count;
int call_virtual_meth(void *obj, int i);
void* create_DtorObj();

void (*DtorObj_vtable[2])();
void DtorObj_set_vflag(void* self, int i);
void DtorObj_set_vflags(void* self, char* flags);
void* DtorObj_88_DtorObj();
void DtorObj_88_delete(void *self);
int DtorObj_88_non_virtual_meth(void *self, int i);
int DtorObj_88_virtual_meth(void *self, int i);

void* NoDtorObj_88_NoDtorObj();
void NoDtorObj_88_delete(void *obj);
''')

clib = ffi.verify('''
extern int deleted_count;
int call_virtual_meth(void *obj, int i);
void* create_DtorObj();

extern void (*DtorObj_vtable[2])();
void DtorObj_set_vflag(void* self, int i);
void DtorObj_set_vflags(void* self, char* flags);
void* DtorObj_88_DtorObj();
void DtorObj_88_delete(void *self);
int DtorObj_88_non_virtual_meth(void *self, int i);
int DtorObj_88_virtual_meth(void *self, int i);

void* NoDtorObj_88_NoDtorObj();
void NoDtorObj_88_delete(void *obj);
''', sources=[path.join(path.dirname(__file__), 'test_cppwrapper.cpp')])


def collect_all_wrappers():
    while True:
        deleted_count = clib.deleted_count
        gc.collect()
        if deleted_count == clib.deleted_count:
            break


class NoDtorObj(CppWrapper):
    def __init__(self):
        cpp_obj = clib.NoDtorObj_88_NoDtorObj()
        CppWrapper.__init__(self, cpp_obj)

    def __del__(self):
        if self._py_owned:
            clib.NoDtorObj_88_delete(self._cpp_obj)
        CppWrapper.__del__(self)

class NoDtorObjSubClass(NoDtorObj):
    pass

class DtorObj(CppWrapper):
    _vtable = clib.DtorObj_vtable

    def __init__(self):
        cpp_obj = clib.DtorObj_88_DtorObj()
        CppWrapper.__init__(self, cpp_obj)

    def __del__(self):
        if self._py_owned:
            clib.DtorObj_88_delete(self._cpp_obj)
        CppWrapper.__del__(self)

    def _set_vflag(self, i):
        clib.DtorObj_set_vflag(self._cpp_obj, i)

    def _set_vflags(self, flags):
        clib.DtorObj_set_vflags(self._cpp_obj, flags)

    @VirtualDispatcher(0)
    @ffi.callback('void(*)(void*)')
    def _virtual___dtor__(ptr):
        self = obj_from_ptr(ptr, DtorObj)
        self.__del__()

    def non_virtual_meth(self, i):
        return clib.DtorObj_88_non_virtual_meth(self._cpp_obj, i)

    @VirtualMethod(1)
    def virtual_meth(self, i):
        return clib.DtorObj_88_virtual_meth(self._cpp_obj, i)

    @VirtualDispatcher(1)
    @ffi.callback("int(*)(void*, int)")
    def _virtual_virtual_meth(ptr, i):
        self = obj_from_ptr(ptr, DtorObj)
        return self.virtual_meth(i)

class DtorObjSubClass(DtorObj):
    def virtual_meth(self, i):
        return i * i

class TestMethodCalls(object):
    def test_nonvirtual_method(self):
        obj = DtorObj()
        assert obj.non_virtual_meth(10) == 10

    def test_virtual_method(self):
        obj = DtorObj()
        assert obj.virtual_meth(10) == 10

    def test_replacing_instance_virtual_method(self):
        def override(i):
            return -i

        obj = DtorObj()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 10
        obj.virtual_meth = override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

    def test_replacing_class_virtual_method(self):
        class TmpDtorObjSubClass(DtorObj):
            pass
        def override(self, i):
            return -i

        obj = TmpDtorObjSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 10

        TmpDtorObjSubClass.virtual_meth = override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

        obj = TmpDtorObjSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

    def test_replacing_overriden_instance_virtual_method(self):
        def override(i):
            return -i

        obj = DtorObjSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 100

        obj.virtual_meth = override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

    def test_replacing_class_and_instance_virtual_method(self):
        class TmpDtorObjSubClass(DtorObj):
            pass
        def override(i):
            return -i
        def cls_override(self, i):
            return i + 1

        obj = TmpDtorObjSubClass()
        obj.virtual_meth = override
        TmpDtorObjSubClass.virtual_meth = cls_override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

    def test_call_virtual_method_from_super(self):
        class TmpDtorObjSubClass(DtorObj):
            def virtual_meth(self, i):
                return super(TmpDtorObjSubClass, self).virtual_meth(i - 1)
        def override(i):
            return -i

        obj = TmpDtorObjSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 9
        assert super(TmpDtorObjSubClass, obj).virtual_meth(10) == 10

        obj.virtual_meth = override
        assert super(TmpDtorObjSubClass, obj).virtual_meth(10) == 10
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == -10

    def test_overridden_virtual_method(self):
        obj = DtorObjSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 100

    def test_call_virtual_method_double_subclass(self):
        class DtorObjSubClassSubClass(DtorObjSubClass):
            pass

        obj = DtorObjSubClassSubClass()
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 100

    def test_override_not_py_created(self):
        def override(self, i):
            return -i

        obj = obj_from_ptr(clib.create_DtorObj(), DtorObj)
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 10
        obj.virtual_meth = override
        assert clib.call_virtual_meth(obj._cpp_obj, 10) == 10

class TestCppObjectLifetimes(object):
    def test_cpp_owned(self):
        collect_all_wrappers()
        deleted_count = clib.deleted_count
        obj = NoDtorObj()
        give_ownership(obj)
        del obj
        collect_all_wrappers()

        assert deleted_count == clib.deleted_count

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
        give_ownership(obj, None)

        del obj
        collect_all_wrappers()
        assert wk() is None

    def test_no_parent_cpp_owned_external_ref(self):
        obj = DtorObj()
        wk = weakref.ref(obj)
        give_ownership(obj, None, True)

        del obj
        collect_all_wrappers()
        assert wk() is not None

    def test_py_owned_parent_dies(self):
        # Only test C++ owned child objects; Python owned objects don't have
        # parents
        parent = NoDtorObj()
        child = NoDtorObj()
        give_ownership(child, parent)

        pwk = weakref.ref(parent)
        cwk = weakref.ref(child)
        del child
        del parent
        collect_all_wrappers()

        assert pwk() is None
        assert cwk() is None

    def test_cpp_owned_dtor_called(self):
        collect_all_wrappers()
        deleted_count = clib.deleted_count
        obj = DtorObj()
        give_ownership(obj)
        wk = weakref.ref(obj)
        ptr = obj._cpp_obj
        del obj

        clib.DtorObj_88_delete(ptr)
        collect_all_wrappers()
        assert deleted_count + 1 == clib.deleted_count
        assert wk() is None

    def test_cpp_owned_parent_dies(self):
        parent = DtorObj()
        child = NoDtorObj()

        give_ownership(parent, None, True)
        give_ownership(child, parent)

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

        give_ownership(parent, None, True)
        give_ownership(child1, parent)
        give_ownership(child2, parent)

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

    def test_change_parent(self):
        parent1 = NoDtorObj()
        parent2 = NoDtorObj()
        child = NoDtorObj()
        wk = weakref.ref(child)

        give_ownership(child, parent1)
        give_ownership(child, parent2)

        del parent1
        del child
        collect_all_wrappers()
        assert wk() is not None

        del parent2
        collect_all_wrappers()
        assert wk() is None

class TestObjectLookup(object):
    def test_object_recall(self):
        obj = NoDtorObj()
        ptr = obj._cpp_obj
        obj2 = obj_from_ptr(obj._cpp_obj, NoDtorObj)

        assert obj is obj2

    def test_object_recall_from_superclass(self):
        obj = NoDtorObj()
        ptr = obj._cpp_obj
        obj2 = obj_from_ptr(obj._cpp_obj, CppWrapper)

        assert obj is obj2

    def test_object_recall_from_subclass(self):
        obj = NoDtorObj()
        ptr = obj._cpp_obj
        obj2 = obj_from_ptr(obj._cpp_obj, NoDtorObjSubClass)
        obj3 = obj_from_ptr(obj._cpp_obj, NoDtorObj)

        assert obj is not obj2
        assert obj2 is obj3

    def test_object_recall_override(self):
        obj = DtorObj()
        ptr = obj._cpp_obj

        assert obj_from_ptr(ptr) is obj

        dup = obj_from_ptr(ptr, NoDtorObj)
        assert dup is not obj
        assert obj_from_ptr(ptr) is dup
