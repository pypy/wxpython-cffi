import os
import sys
import imp
import pickle
import pytest

# Manually add the top-level directory to our path so we can import etgtools
# modules
sys.path.append("../..")
from etgtools import extractors, cffi_bindgen
from etgtools.extractors import (
    ModuleDef, DefineDef, ClassDef, MethodDef, FunctionDef, ParamDef,
    CppMethodDef, MemberVarDef, GlobalVarDef, PyPropertyDef, PyFunctionDef,
    PyClassDef, PyCodeDef, EnumDef, EnumValueDef)

class TestBindGen(object):
    @classmethod
    def setup_class(cls):
        cls.tmpdir = pytest.ensuretemp('build', dir=True)
        cls.gen = cls.create_generator()
        cls.mod = cls.build_module()

    @classmethod
    def create_generator(cls):
        module = ModuleDef('bindgen_test', '_core', '_core')
        module.addHeaderCode('#include <test_bindgen.h>')

        module.addItem(DefineDef(
            name='prefixedSOME_INT', pyName='SOME_INT'))

        module.addItem(EnumDef(name='BOOLEAN', items=[
            EnumValueDef(name='BOOL_TRUE'),
            EnumValueDef(name='BOOL_FALSE')]))

        module.addItem(GlobalVarDef(
            type='const char *', name='global_str', pyName='global_str'))
        module.addItem(GlobalVarDef(
            type='const CtorsClass', name='global_wrapped_obj',
            pyName='global_wrapped_obj'))

        module.addItem(FunctionDef(
            type='int', argsString='()', name='simple_global_func',
            pyName='simple_global_func'))
        module.addItem(FunctionDef(
            type='float', argsString='(int i, double j)',
            name='global_func_with_args', pyName='global_func_with_args',
            items=[ParamDef(type='int', name='i'),
                   ParamDef(type='double', name='j')]))
        module.addItem(FunctionDef(
            type='int', argsString='(const char *s)',
            name='global_func_with_default', pyName='global_func_with_default',
            items=[ParamDef(type='const char *', name='s',
                           default='other_global_str')]))
        f = FunctionDef(
            type='double', argsString='()',
            name='custom_code_global_func', pyName='custom_code_global_func')
        f.setCppCode("return custom_code_global_func() - 1;")
        module.addItem(f)
        module.addItem(CppMethodDef(
            'short', 'global_cppmethod', '(short x, short y)',
            body="return (x * y)/(x + y);"))
        module.addItem(FunctionDef(
            type='int', argsString='()',
            name='overloaded_func', pyName='overloaded_func',
            overloads=[FunctionDef(
                type='double', argsString='(double i)',
                name='overloaded_func', pyName='overloaded_func',
                items=[ParamDef(type='int', name='i')])]))

        module.addPyFunction('global_pyfunc', '()', 'return "42"')

        module.addGlobalStr("other_global_str")

        c = ClassDef(name='SimpleClass')
        c.addItem(MethodDef(
            type='int', argsString='(double f)',
            name='simple_method', pyName='simple_method',
            items=[ParamDef(type='double', name='f')]))

        module.addItem(c)

        module.addItem(ClassDef(name='SimpleSubclass', bases=['SimpleClass']))

        c = ClassDef(name='VMethClass')
        c.addItem(MethodDef(
            type='int', argsString='(int i)',
            name='virtual_method', pyName='virtual_method', isVirtual=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='int', argsString='(int i)',
            name='call_virtual', pyName='call_virtual',
            items=[ParamDef(type='int', name='i')]))

        module.addItem(c)

        module.addItem(ClassDef(name='VMethSubclass', bases=['VMethClass']))

        c = ClassDef(name='PVMethClass')
        c.addItem(MethodDef(
            protection='protected', type='int', argsString='(int i)',
            name='protected_virtual_method', pyName='protected_virtual_method',
            isVirtual=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='int', argsString='(int i)',
            name='call_method', pyName='call_method',
            items=[ParamDef(type='int', name='i')]))

        module.addItem(c)

        c = ClassDef(name='PMethClass')
        c.addItem(MethodDef(
            protection='protected', type='char', argsString='(char c)',
            name='protected_method', pyName='protected_method',
            items=[ParamDef(type='char', name='c')]))

        module.addItem(c)

        c = ClassDef(name='CtorsClass')
        c.addItem(MethodDef(
            type='', argsString='()', isOverloaded=True,
            name='CtorsClass', isCtor=True,
            overloads=[
                MethodDef(type='', argsString='(const CtorsClass &other)',
                name='CtorsClass', isCtor=True,
                items=[ParamDef(type='const CtorsClass &', name='other')]),
                MethodDef(type='', argsString='(int i)',
                name='CtorsClass', isCtor=True,
                items=[ParamDef(type='int', name='i')])]))
        c.addItem(MethodDef(
            type='int', argsString='()',
            name='get', pyName='get'))
        m = MethodDef(
            type='double', argsString='(double f)',
            name='custom_code_meth', pyName='custom_code_meth',
            items=[ParamDef(type='double', name='f')])
        m.setCppCode('return self->get() * f;')
        c.addCppMethod('double', 'cppmethod', '()', 'return self->get() * 2;')
        c.addPyMethod('double_i', '(self)', 'return self.get() * 2')
        c.addItem(m)

        module.addItem(c)

        c = ClassDef(name='PCtorClass')
        c.addItem(MethodDef(
            type='', argsString='(int i)',
            protection='protected', name='PCtorClass', isCtor=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='int', argsString='()',
            name='get', pyName='get'))
        module.addItem(c)

        c = ClassDef(name='ReturnWrapperClass')
        c.addItem(MethodDef(
            type='', argsString='(int i)',
            name='ReturnWrapperClass', isCtor=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='int', argsString='()',
            name='get', pyName='get'))
        c.addItem(MethodDef(
            type='ReturnWrapperClass', argsString='(int i)',
            name='new_by_value', pyName='new_by_value', isStatic=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='ReturnWrapperClass *', argsString='(int i)',
            name='new_by_ptr', pyName='new_by_ptr', isStatic=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='ReturnWrapperClass &', argsString='(int i)',
            name='new_by_ref', pyName='new_by_ref', isStatic=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='const ReturnWrapperClass &', argsString='(int i)',
            name='new_by_cref', pyName='new_by_cref', isStatic=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='ReturnWrapperClass',
            argsString='()',
            name='self_by_value', pyName='self_by_value'))
        c.addItem(MethodDef(
            type='ReturnWrapperClass *',
            argsString='()',
            name='self_by_ptr', pyName='self_by_ptr'))
        c.addItem(MethodDef(
            type='ReturnWrapperClass &',
            argsString='()',
            name='self_by_ref', pyName='self_by_ref'))
        c.addItem(MethodDef(
            type='const ReturnWrapperClass &',
            argsString='()',
            name='self_by_cref', pyName='self_by_cref'))

        module.addItem(c)

        c = ClassDef(name='VDtorClass')
        c.addItem(MethodDef(
            type='', argsString='()',
            name='~VDtorClass', isVirtual=True, isDtor=True))

        module.addItem(c)

        c = ClassDef(name='MemberVarClass')
        c.addItem(MethodDef(
            type='', argsString='(int i)',
            name='MemberVarClass', isCtor=True,
            items=[ParamDef(type='int', name='i')]))
        c.addItem(MethodDef(
            type='int', argsString='()',
            name='Get_i', pyName='Get_i'))
        c.addItem(MethodDef(
            type='void', argsString='(int i)',
            name='Set_i', pyName='Set_i',
            items=[ParamDef(type='int', name='i')]))
        c.addPyMethod('Get_i_pymeth', '(self)', 'return self._i')
        c.addPyMethod('Set_i_pymeth', '(self, i)', 'self._i = i')
        c.addItem(MemberVarDef(
            type='int', name='m_i', pyName='m_i'))

        c.addAutoProperties()
        module.addItem(c)

        c = ClassDef(name='NestedClassReturnDependant')
        c.addItem(MethodDef(
            type='NestedClassesOuter::NestedClassesInner', argsString='()',
            name='get', pyName='get'))
        module.addItem(c)

        c = ClassDef(name='NestedClassArgDependant')
        c.addItem(MethodDef(
            type='int', argsString='(const NestedClassesOuter::NestedClassesInner &i)',
            name='get', pyName='get', items=[ParamDef(
                type='const NestedClassesOuter::NestedClassesInner &',
                name='i')]))
        module.addItem(c)

        c = ClassDef(name='NestedClassesOuter')
        ic = ClassDef(name='NestedClassesInner')
        c.innerclasses = [ic]
        ic.addItem(MethodDef(
            type='int', argsString='()', name='vmeth', pyName='vmeth',
            isVirtual=True))
        ic.addItem(MethodDef(
            type='int', argsString='()', name='call_vmeth',
            pyName='call_vmeth'))
        ic.addItem(MemberVarDef(type='int', name='m_i', pyName='m_i'))
        ic.addPyMethod(
            type='int', argsString='(self)', name='Getpyi',
            body='return self.m_i')
        ic.addPyMethod(
            type='void', argsString='(self, i)', name='Setpyi',
            body='self.m_i = i')
        ic.addItem(MethodDef(
            type='int', argsString='()',
            name='Get_i', pyName='Get_i'))
        ic.addItem(MethodDef(
            type='void', argsString='(int i)',
            name='Set_i', pyName='Set_i',
            items=[ParamDef(type='int', name='i')]))
        ic.addItem(MethodDef(
            type='void', argsString='()',
            name='overloaded', pyName='overloaded', isOverloaded=True,
            overloads=[MethodDef(
                type='void', argsString='(double f)',
                name='overloaded', pyName='overloaded',
                items=[ParamDef(type='double', name='f')])]))

        ic.addAutoProperties()
        module.addItem(c)

        c = ClassDef(name='ClassWithEnum')
        c.addItem(EnumDef(name='BOOLEAN', items=[
            EnumValueDef(name='BOOL_TRUE'),
            EnumValueDef(name='BOOL_FALSE')]))
        module.addItem(c)

        module.addPyCode('global_pyclass_int = global_pyclass_inst.i')
        module.addPyCode('global_pyclass_inst = PyClass(9)', order=20)

        module.addPyClass('PyClass', [], 'PyClass docstring', order=10, items=[
            PyCodeDef('SOME_INT = 9'),
            PyFunctionDef('__init__', '(self, i)', 'self._i = i'),
            PyFunctionDef('geti', '(self)', 'return self._i'),
            PyFunctionDef('seti', '(self, i)', 'self._i = i'),
            PyPropertyDef(name='i', getter='geti', setter='seti')])

        mod_path = cls.tmpdir.join('%s.def' % module.name)
        with mod_path.open('w') as f:
            pickle.dump(module, f)

        gen = cffi_bindgen.CffiModuleGenerator(module.name,
                                               str(cls.tmpdir.join('%s.def')))
        gen.init({})
        return gen

    @classmethod
    def build_module(cls):
        cpp_path = cls.tmpdir.join('_core.cpp')
        py_path = cls.tmpdir.join('_core.py')

        test_dir = os.path.dirname(__file__)
        sources = [str(cpp_path), os.path.join(test_dir, 'test_bindgen.cpp')]
        include_dirs = [test_dir]
        tmpdir = str(cls.tmpdir)

        with cpp_path.open('w') as cpp_file, py_path.open('w') as py_file:
            # Use distutis via cffi to build the cpp code
            cls.gen.writeFiles(
                py_file, cpp_file,
                'sources=["%s"], include_dirs=["%s"], tmpdir="%s"' %
                ('", "'.join(sources), '", "'.join(include_dirs), tmpdir))

        return py_path.pyimport()

    def test_define(self):
        assert self.mod.SOME_INT == 15

    def test_enum(self):
        assert self.mod.BOOL_TRUE == -1
        assert self.mod.BOOL_FALSE == -2

    def test_globalvar(self):
        assert self.mod.global_str == 'string'

    def test_simple_global_func(self):
        assert self.mod.simple_global_func() == 10

    def test_global_func_with_args(self):
        assert self.mod.global_func_with_args(10, 2.0) == 20
        assert self.mod.global_func_with_args(12, .25) == 3
        assert self.mod.global_func_with_args(14, .25) == (14 * .25)

    def test_global_func_with_default(self):
        assert self.mod.global_func_with_default() == 5
        assert self.mod.global_func_with_default('test') == 4

    def test_custom_code_func(self):
        assert self.mod.custom_code_global_func() == 1

    def test_global_cppmethod(self):
        obj =  self.mod.CtorsClass(4)
        assert obj.cppmethod() == 8

    def test_simple_class_init(self):
        self.mod.SimpleClass()

    def test_simple_subclass_init(self):
        self.mod.SimpleSubclass()

    def test_simple_method(self):
        c = self.mod.SimpleClass()
        assert c.simple_method(5.5) == 5

    def test_simple_subclass_method(self):
        obj = self.mod.SimpleSubclass()
        assert obj.simple_method(5.5) == 5

    def test_virtual_method_direct_call(self):
        c = self.mod.VMethClass()
        assert c.virtual_method(5) == -5
        assert c.call_virtual(5) == -5

    def test_override_virtual_method(self):
        class VMethSubClass(self.mod.VMethClass):
            def virtual_method(self, i):
                return i * 2

        c = VMethSubClass()
        assert c.virtual_method(5) == 10
        assert c.call_virtual(5) == 10

    def test_subclass_virtual_method_direct_call(self):
        c = self.mod.VMethSubclass()
        assert c.virtual_method(5) == -5
        assert c.call_virtual(5) == -5

    def test_protected_method(self):
        obj = self.mod.PMethClass()
        assert obj.protected_method('a') == 'A'

    def test_protected_ctor(self):
        assert self.mod.PCtorClass(15).get() == 15

    def test_protected_virtual_method_direct_call(self):
        c = self.mod.PVMethClass()
        assert c.protected_virtual_method(5) == -5
        assert c.call_method(5) == -5

    def test_override_proected_virtual_method(self):
        class PVMethSubClass(self.mod.PVMethClass):
            def protected_virtual_method(self, i):
                return i * 2

        c = PVMethSubClass()
        assert c.protected_virtual_method(5) == 10
        assert c.call_method(5) == 10

    def test_overloaded_ctors(self):
        obj = self.mod.CtorsClass()
        obj2 = self.mod.CtorsClass(obj)
        assert obj.get() == 0
        assert obj.get() == obj2.get()

        obj = self.mod.CtorsClass(12)
        obj2 = self.mod.CtorsClass(obj)
        assert obj.get() == 12
        assert obj.get() == obj2.get()

        obj = self.mod.CtorsClass(5.0)
        obj2 = self.mod.CtorsClass(obj)
        assert obj.get() == 5
        assert obj.get() == obj2.get()

    def test_custom_code_method(self):
        obj = self.mod.CtorsClass(15)
        assert obj.custom_code_meth(.2) == 3
        obj = self.mod.CtorsClass(4)
        assert obj.custom_code_meth(1.5) == 6

    def test_cpp_method(self):
        obj = self.mod.CtorsClass(15)

    def test_overloaded_func(self):
        assert self.mod.overloaded_func() == 20
        assert self.mod.overloaded_func(12) == 6

    def test_pymethod(self):
        obj = self.mod.CtorsClass(100)
        assert obj.double_i() == 200

    def test_pyclass(self):
        obj = self.mod.PyClass(99)
        assert obj.geti() == obj.i == 99
        obj.i = 88
        assert obj.geti() == obj.i == 88

    def test_pycode(self):
        assert self.mod.global_pyclass_int == 9
        assert self.mod.global_pyclass_inst.i == 9

    def test_global_pyfunc(self):
        assert self.mod.global_pyfunc() == '42'

    def test_returned_wrapper(self):
        from_value = self.mod.ReturnWrapperClass.new_by_value(3)
        from_ptr = self.mod.ReturnWrapperClass.new_by_ptr(4)
        from_ref = self.mod.ReturnWrapperClass.new_by_ref(5)
        from_cref = self.mod.ReturnWrapperClass.new_by_cref(5)

        assert from_value.get() == 3
        assert from_ptr.get() == 4
        assert from_ref.get() == 5
        assert from_cref.get() == 5

        obj = self.mod.ReturnWrapperClass(15)
        from_value = obj.self_by_value()
        from_ptr = obj.self_by_ptr()
        from_ref = obj.self_by_ref()
        from_cref = obj.self_by_cref()

        assert obj is not from_value
        assert obj is from_ptr
        assert obj is from_ref
        assert obj is not from_cref

        assert obj._py_owned
        # TODO: uncomment these assertions when I start implementing object
        #       ownership stuff
        #assert from_value._py_owned
        #assert from_cref._py_owned

    def test_membervar(self):
        obj = self.mod.MemberVarClass(5)
        assert obj.m_i == 5
        obj.m_i = 6
        assert obj.m_i == 6

    def test_property(self):
        obj = self.mod.MemberVarClass(9)
        assert obj._i == 9

        obj._i += 11
        assert obj._i == 20
        assert obj.m_i == 20

    def test_pyproperty(self):
        obj = self.mod.MemberVarClass(9)
        assert obj._i_pymeth == 9

        obj._i_pymeth += 11
        assert obj._i_pymeth == 20
        assert obj.m_i == 20

    def test_nested_class(self):
        class InnerClassSubclass(self.mod.NestedClassesOuter.NestedClassesInner):
            def vmeth(self):
                return 121

        obj = self.mod.NestedClassesOuter()
        obj = self.mod.NestedClassesOuter.NestedClassesInner()
        assert obj.vmeth() == 142
        assert obj.call_vmeth() == 142

        obj.pyi = 169
        assert obj.m_i == 169
        assert obj._i == 169
        obj.m_i = 221
        assert obj.pyi == 221
        assert obj._i == 221
        obj._i = 99
        assert obj.pyi == 99
        assert obj.m_i == 99

        obj.overloaded()
        assert obj.m_i == -10
        obj.overloaded(-.2)
        assert obj.m_i == 2

        obj = InnerClassSubclass()
        assert obj.vmeth() == 121
        assert obj.call_vmeth() == 121

    def test_nested_enum(self):
        assert self.mod.ClassWithEnum.BOOL_TRUE == -10
        assert self.mod.ClassWithEnum.BOOL_FALSE == -20
