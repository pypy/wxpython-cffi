import gc
import os
import sys
import imp
import weakref
import pickle
import pytest

import wrapper_lib

# Manually add the top-level directory to our path so we can import etgtools
# modules
sys.path.append("../..")
from etgtools import extractors, cffi_bindgen
from etgtools.generators import nci
from etgtools.extractors import (
    ModuleDef, DefineDef, ClassDef, MethodDef, FunctionDef, ParamDef,
    CppMethodDef, MemberVarDef, GlobalVarDef, PyPropertyDef, PyFunctionDef,
    PyClassDef, PyCodeDef, EnumDef, EnumValueDef, MappedTypeDef_cffi)

from buildtools.config import Config
cfg = Config(noWxConfig=True).ROOT_DIR
INCLUDES_DIR = os.path.join(cfg, 'cffi', 'include')

class TestBindGen(object):
    @classmethod
    def setup_class(cls):
        cls.tmpdir = pytest.ensuretemp('build', dir=True)
        cls.gens = cls.create_generators()
        cls.mod = cls.build_module('_core')
        cls.mod2 = cls.build_module('_extra')

    @classmethod
    def create_generators(cls):
        module = ModuleDef('bindgen_test', '_core', '_core')
        module.addHeaderCode('#include <test_bindgen.h>')

        module.addPyCode('from _core import *', 0)

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
        c.addCppCtor('(char a)', 'return new CtorsClass((int)a);')
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
            type='const ReturnWrapperClass &', argsString='(int i)',
            name='new_by_nocopy_cref', isStatic=True, noCopy=True,
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
        c.addItem(MethodDef(
            type='const ReturnWrapperClass &',
            argsString='()', noCopy=True,
            name='self_by_nocopy_cref', pyName='self_by_nocopy_cref'))

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

        c = ClassDef(name='OperatorsClass')
        c.addItem(MethodDef(
            type='', argsString='(int x, int y)',
            name='OperatorsClass', isCtor=True, items=[
                ParamDef(type='int', name='x'),
                ParamDef(type='int', name='y')]))
        c.addItem(MethodDef(
            type='OperatorsClass &', argsString='(const OperatorsClass &rhs)',
            name='operator+=', items=[
                ParamDef(type='const OperatorsClass &', name='rhs')]))
        c.addItem(MethodDef(
            type='OperatorsClass &', argsString='(const OperatorsClass &rhs)',
            name='operator-=', items=[
                ParamDef(type='const OperatorsClass &', name='rhs')]))
        c.addItem(MemberVarDef(name='x', type='int'))
        c.addItem(MemberVarDef(name='y', type='int'))
        module.addItem(c)

        c = ClassDef(name='ClassWithEnum')
        c.addItem(EnumDef(name='BOOLEAN', items=[
            EnumValueDef(name='BOOL_TRUE'),
            EnumValueDef(name='BOOL_FALSE')]))
        module.addItem(c)

        c = ClassDef(name='PyIntClass')
        c.addItem(MethodDef(
            type='char', argsString='(char c)', name='noPyInt',
            items=[ParamDef(type='char', name='c')]))
        c.addItem(MethodDef(
            type='char', argsString='(char c)', name='onReturn', pyInt=True,
            items=[ParamDef(type='char', name='c')]))
        c.addItem(MethodDef(
            type='char', argsString='(char c)', name='onParameter',
            items=[ParamDef(type='char', name='c', pyInt=True)]))
        c.addItem(MethodDef(
            type='char', argsString='(char c)', name='onBoth', pyInt=True,
            items=[ParamDef(type='char', name='c', pyInt=True)]))
        c.addItem(MethodDef(
            type='char', argsString='()', name='overloaded', pyInt=True,
            overloads=[
                MethodDef(
                    type='char', argsString='(char c)', name='overloaded',
                    pyInt=True,
                    items=[ParamDef(type='char', name='c', pyInt=True)])]))
        module.addItem(c)

        c = ClassDef(name='ArrayClass')
        c.addItem(MethodDef(
            name='ArrayClass', argsString='()', isCtor=True, overloads=[
                MethodDef(name='ArrayClass', argsString='(int i)', isCtor=True,
                         items=[ParamDef(type='int', name='i')])]))
        c.addItem(MethodDef(
            type='int', argsString='(ArrayClass *objs, int len)',
            name='sum', isStatic=True,
            items=[ParamDef(type='ArrayClass *', name='objs', array=True),
                   ParamDef(type='int', name='len', arraySize=True)]))
        c.addItem(MethodDef(
            type='int', argsString='(ArrayClass *objs, int len)',
            name='sum_virt', isVirtual=True,
            items=[ParamDef(type='ArrayClass *', name='objs', array=True),
                   ParamDef(type='int', name='len', arraySize=True)]))
        c.addItem(MethodDef(
            type='int', argsString='(ArrayClass *objs, int len)',
            name='call_sum_virt',
            items=[ParamDef(type='ArrayClass *', name='objs', array=True),
                   ParamDef(type='int', name='len', arraySize=True)]))
        c.addItem(MemberVarDef(type='int', name='m_i'))
        module.addItem(c)

        c = ClassDef(name='InOutClass')
        c.addItem(MethodDef(
            type='void', argsString='(int *num)', name='double_ptr',
            isVirtual=True,
            items=[ParamDef(type='int *', name='num', inOut=True)],
            overloads=[
                MethodDef(
                    type='void', argsString='(CtorsClass *num)',
                    name='double_ptr', isVirtual=True, items=[
                    ParamDef(type='CtorsClass *', name='num', inOut=True)]),
                MethodDef(
                type='void', argsString='(Vector *vec)', isVirtual=True,
                name='double_ptr', items=[
                    ParamDef(type='Vector *', name='vec', inOut=True)])]))
        c.addItem(MethodDef(
            type='void', argsString='(int &num)', name='double_ref',
            isVirtual=True,
            items=[ParamDef(type='int &', name='num', inOut=True)],
            overloads=[
                MethodDef(
                type='void', argsString='(CtorsClass *num)', isVirtual=True, 
                name='double_ref', items=[
                    ParamDef(type='CtorsClass &', name='num', inOut=True)]),
                MethodDef(
                type='void', argsString='(Vector &vec)',
                name='double_ref', isVirtual=True, items=[
                    ParamDef(type='Vector &', name='vec', inOut=True)])]))
        c.addItem(MethodDef(
            type='void', argsString='(int *num)', name='call_double_ptr',
            items=[ParamDef(type='int *', name='num', inOut=True)],
            overloads=[
                MethodDef(
                    type='void', argsString='(CtorsClass *num)',
                    name='call_double_ptr', items=[
                    ParamDef(type='CtorsClass *', name='num', inOut=True)]),
                MethodDef(
                type='void', argsString='(Vector *vec)',
                name='call_double_ptr', items=[
                    ParamDef(type='Vector *', name='vec', inOut=True)])]))
        c.addItem(MethodDef(
            type='void', argsString='(int &num)', name='call_double_ref',
            items=[ParamDef(type='int &', name='num', inOut=True)],
            overloads=[
                MethodDef(
                type='void', argsString='(CtorsClass *num)',
                name='call_double_ref', items=[
                    ParamDef(type='CtorsClass &', name='num', inOut=True)]),
                MethodDef(
                type='void', argsString='(Vector &vec)',
                name='call_double_ref', items=[
                    ParamDef(type='Vector &', name='vec', inOut=True)])]))
        module.addItem(c)

        c = ClassDef(name='AllowNoneClass')
        c.addItem(MethodDef(
            type='long', argsString='(SmartVector *v)', name="get_addr_ptr",
            items=[ParamDef(type='SmartVector *', name='v')]))
        c.addItem(MethodDef(
            type='long', argsString='(SmartVector &v)', name="get_addr_ref",
            items=[ParamDef(type='SmartVector &', name='v')]))
        c.addItem(MethodDef(
            type='long', argsString='(AllowNoneSmartVector *v)',
            name="allow_none_get_addr_ptr",
            items=[ParamDef(type='AllowNoneSmartVector *', name='v')]))
        c.addItem(MethodDef(
            type='long', argsString='(AllowNoneSmartVector &v)',
            name="allow_none_get_addr_ref",
            items=[ParamDef(type='AllowNoneSmartVector &', name='v')]))
        module.addItem(c)

        module.addItem(ClassDef(name='AbstractClass', abstract=True))
        module.addItem(ClassDef(name='ConcreteSubclass',
                                bases=['AbstractClass']))

        c = ClassDef(name="PureVirtualClass")
        c.addItem(MethodDef(
            type='int', argsString='()', name='purevirtual', isVirtual=True,
            isPureVirtual=True))
        c.addItem(MethodDef(
            type='int', argsString='()', name='call_purevirtual'))
        module.addItem(c)

        c = ClassDef(
            name='SmartVector',
            convertPy2Cpp="""\
            return SmartVector(py_obj[0], py_obj[1])
            """,
            instancecheck="""\
            import collections
            return isinstance(obj, collections.Sequence) and len(obj) == 2
            """)
        c.addItem(MethodDef(
            name='SmartVector', argsString='(int x_, int y_)', isCtor=True,
            items=[ParamDef(type='int', name='x_'),
                   ParamDef(type='int', name='y_')]))
        c.addItem(MemberVarDef(type='int', name='x'))
        c.addItem(MemberVarDef(type='int', name='y'))
        module.addItem(c)

        c = ClassDef(
            name='AllowNoneSmartVector',
            allowNone=True,
            convertPy2Cpp="""\
            if py_obj is None:
                return AllowNoneSmartVector(-1, -1)
            return AllowNoneSmartVector(py_obj[0], py_obj[1])
            """,
            instancecheck="""\
            import collections
            return isinstance(obj, collections.Sequence) and len(obj) == 2
            """)
        c.addItem(MethodDef(
            name='AllowNoneSmartVector', argsString='(int x_, int y_)',
            isCtor=True, items=[ParamDef(type='int', name='x_'),
                                ParamDef(type='int', name='y_')]))
        c.addItem(MemberVarDef(type='int', name='x'))
        c.addItem(MemberVarDef(type='int', name='y'))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='SmartVector', argsString='(SmartVector &vec)',
            name='double_vector', items=[ParamDef(
                type='SmartVector &', name='vec')]))

        c = ClassDef(name='KeepReferenceClass')
        c.addItem(MethodDef(
            type='void', argsString='(KeepReferenceClass &i)', name='keep_ref',
            items=[
                ParamDef(type='KeepReferenceClass &', name='i',
                        keepReference=True)]))
        c.addItem(MethodDef(
            type='void', argsString='(KeepReferenceClass &i)',
            name='keep_ref2', items=[
                ParamDef(type='KeepReferenceClass &', name='i',
                        keepReference=True)]))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='void', argsString='(KeepReferenceClass &i)',
            name='global_keep_ref', items=[
                ParamDef(type='KeepReferenceClass &', name='i',
                        keepReference=True)]))

        c = ClassDef(name='TransferClass')
        c.addItem(MethodDef(
            argsString='()', name='TransferClass', isCtor=True, overloads=[
            MethodDef(
                argsString='(int i)', name='TransferClass',
                isCtor=True, transfer=True, items=[
                    ParamDef(type='int', name='i')]),
            MethodDef(
                argsString='(TransferClass * i)', name='TransferClass',
                isCtor=True, items=[
                    ParamDef(type='TransferClass *', name='i',
                             transferThis=True)])]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)',
            name="transfer_param", items=[
                ParamDef(type='TransferClass *', name='obj', transfer=True)]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)', isStatic=True,
            name="static_transfer_param", items=[
                ParamDef(type='TransferClass *', name='obj', transfer=True)]))
        c.addItem(MethodDef(
            type='TransferClass *', argsString='(TransferClass *obj)',
            name="transfer_return", transfer=True, items=[
                ParamDef(type='TransferClass *', name='obj')]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)',
            name="transferback_param", items=[
                ParamDef(type='TransferClass *', name='obj',
                         transferBack=True)]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)',
            name="transferthis_param", items=[
                ParamDef(type='TransferClass *', name='obj',
                         transferThis=True)]))
        c.addItem(MethodDef(
            type='void', argsString='()',
            name="transferthis_return", transferThis=True))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)', isStatic=True,
            name="static_transferback_param", items=[
                ParamDef(type='TransferClass *', name='obj',
                         transferBack=True)]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *obj)',
            name="transferback_return", items=[
                ParamDef(type='TransferClass *', transferBack=True, name='obj')]))
        c.addItem(MethodDef(
            type='TransferClass *', argsString='(TransferClass *obj)', isStatic=True,
            name="static_transferback_return", transferBack=True, items=[
                ParamDef(type='TransferClass *', name='obj')]))
        c.addItem(MethodDef(
            type='void', argsString='(TransferClass *objs, int count)',
            name='transfer_array', items=[
                ParamDef(type='TransferClass *', name='objs', array=True,
                         transfer=True),
                ParamDef(type='int', name='count', arraySize=True)],
            overloads=[MethodDef(
                type='void', argsString='(Vector *objs, int count)',
                name='transfer_array', items=[
                    ParamDef(type='Vector *', name='objs', array=True,
                            transfer=True),
                    ParamDef(type='int', name='count', arraySize=True)])]))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='void', argsString='(TransferClass *obj)',
            name="global_transfer_param", items=[
                ParamDef(type='TransferClass *', name='obj', transfer=True)]))
        module.addItem(FunctionDef(
            type='void', argsString='(TransferClass *obj)',
            name="global_transferback_param", items=[
                ParamDef(type='TransferClass *', name='obj',
                         transferBack=True)]))
        module.addItem(FunctionDef(
            type='TransferClass *', argsString='(TransferClass *obj)', transferBack=True,
            name="global_transferback_return", items=[
                ParamDef(type='TransferClass *', name='obj')]))

        c = ClassDef(name='FactoryClass')
        c.addItem(MethodDef(
            type='FactoryClass *', argsString='()',  name='make',
            factory=True, isVirtual=True))
        c.addItem(MethodDef(
            type='FactoryClass *', argsString='()',  name='call_make'))
        c.addItem(MethodDef(
            type='FactoryClass *', argsString='(FactoryClass *ref)',
             name='make_keep_ref', factory=True, items=[
                ParamDef(type='FactoryClass *', name='ref', keepReference=True)
            ]))
        c.addItem(MethodDef(
            type='FactoryClass *', argsString='(FactoryClass *ref)',
             name='make_transfer_this', factory=True, items=[
                ParamDef(type='FactoryClass *', name='ref', transferThis=True)
            ]))
        module.addItem(c)

        c = ClassDef(name="DeprecatedClass", deprecated=True)
        c.addItem(MethodDef(
            type='void', argsString='()', name='deprecated_method'))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='void', argsString='()', name='deprecated_func',
            deprecated=True))

        c = ClassDef(name='VirtualCatcherBase')
        c.addItem(MethodDef(
            type='const char*', argsString='()', name='vmeth', isVirtual=True,
            virtualCatcherCode_cffi="""\
            res = self.vmeth()
            if not isinstance(res, str):
                return ""
            else:
                return res.upper()
            """))
        c.addItem(MethodDef(
            type='const char*', argsString='()', name='call_vmeth'))
        module.addItem(c)

        module.addItem(MappedTypeDef_cffi(
            name='string', cType='char *',
            headerCode=["#include <string>\nusing std::string;"],
            py2c="return (ffi.new('char[]', py_obj), None)",
            c2py="""
            ret = ffi.string(cdata)
            clib.free(cdata)
            return ret
            """,
            c2cpp="return new string(cdata);",
            cpp2c="""\
            char *cdata = (char*)malloc(cpp_obj->length() + 1);
            strcpy(cdata, cpp_obj->c_str());
            return cdata;""",
            instancecheck='return isinstance(obj, (str, unicode))',))

        module.addItem(MappedTypeDef_cffi(
            name='Vector', cType='int *',
            py2c="""\
            array = ffi.new('int []', [int(py_obj[0]), int(py_obj[1])])
            return (array, array)""",
            c2py="""\
            ret = (cdata[0], cdata[1])
            clib.free(cdata)
            return ret
            """,
            c2cpp="return new Vector(cdata[0], cdata[1]);",
            cpp2c="""\
            int *cdata = (int*)malloc(sizeof(int) * 2);
            cdata[0] = cpp_obj->i;
            cdata[1] = cpp_obj->j;
            return cdata;""",
            instancecheck="""\
            import collections
            return (isinstance(obj, collections.Sequence) and len(obj) >= 2 and
                    isinstance(obj[0], numbers.Number) and
                    isinstance(obj[1], numbers.Number))
            """,))

        module.addItem(MappedTypeDef_cffi(
            name='IntWrapper', cType='int',
            py2c="return (int(py_obj), None)",
            c2py="return cdata",
            c2cpp="return new IntWrapper(cdata);",
            cpp2c="return cpp_obj->i;",
            instancecheck="""\
            import numbers
            return isinstance(obj, numbers.Number)"""))

        module.addItem(FunctionDef(
            type='int', argsString='(string *str)', name='std_string_len',
            items=[ParamDef(name='str', type='string *')],
            overloads=[FunctionDef(
            type='int', argsString='(string *str), int len',
            name='std_string_len', items=[
                ParamDef(name='str', type='string *', array=True),
                ParamDef(name='len', type='int', arraySize=True)])]))

        c = ClassDef(name='IntWrapperClass')
        c.addItem(MethodDef(
            type='IntWrapper', argsString='(IntWrapper i, IntWrapper &k)',
            name='trivial_mappedtype', isVirtual=True, items=[
                ParamDef(type='IntWrapper', name='i'),
                ParamDef(type='IntWrapper &', name='k', out=True)]))
        c.addItem(MethodDef(
            type='IntWrapper', argsString='(IntWrapper i, IntWrapper &k)',
            name='call_trivial_mappedtype', items=[
                ParamDef(type='IntWrapper', name='i'),
                ParamDef(type='IntWrapper &', name='k', out=True)]))
        c.addItem(MethodDef(
            type='IntWrapper', argsString='(IntWrapper i, IntWrapper &k)',
            name='trivial_inout_mappedtype', isVirtual=True, items=[
                ParamDef(type='IntWrapper', name='i'),
                ParamDef(type='IntWrapper &', name='k', inOut=True)]))
        c.addItem(MethodDef(
            type='IntWrapper', argsString='(IntWrapper i, IntWrapper &k)',
            name='call_trivial_inout_mappedtype', items=[
                ParamDef(type='IntWrapper', name='i'),
                ParamDef(type='IntWrapper &', name='k', inOut=True)]))
        module.addItem(c)

        c = ClassDef(name='OutClass')
        c.addItem(MethodDef(
            type='int', argsString='(int *x, int *y)', name='get_coords_ptr',
            isVirtual=True,
            items=[ParamDef(type='int *', name='x', out=True),
                   ParamDef(type='int *', name='y')]))
        c.addItem(MethodDef(
            type='int', argsString='(int *x, int *y)', name='get_coords_ref',
            isVirtual=True,
            items=[ParamDef(type='int &', name='x', out=True),
                   ParamDef(type='int &', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(string *x, string **y)',
            name='get_mappedtype_ptr', isVirtual=True,
            items=[ParamDef(type='string *', name='x', out=True),
                   ParamDef(type='string **', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(string &x, string *&y)',
            name='get_mappedtype_ref', isVirtual=True,
            items=[ParamDef(type='string &', name='x', out=True),
                   ParamDef(type='string *&', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(CtorsClass *x, CtorsClass **y)',
            name='get_wrappedtype_ptr', isVirtual=True,
            items=[ParamDef(type='CtorsClass *', name='x', out=True),
                   ParamDef(type='CtorsClass **', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(CtorsClass &x, CtorsClass *&y)',
            name='get_wrappedtype_ref', isVirtual=True,
            items=[ParamDef(type='CtorsClass &', name='x', out=True),
                   ParamDef(type='CtorsClass *&', name='y')]))
        c.addItem(MethodDef(
            type='int', argsString='(int *x, int *y)',
            name='call_get_coords_ptr',
            items=[ParamDef(type='int *', name='x', out=True),
                   ParamDef(type='int *', name='y')]))
        c.addItem(MethodDef(
            type='int', argsString='(int *x, int *y)',
            name='call_get_coords_ref',
            items=[ParamDef(type='int &', name='x', out=True),
                   ParamDef(type='int &', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(string *x, string **y)',
            name='call_get_mappedtype_ptr',
            items=[ParamDef(type='string *', name='x', out=True),
                   ParamDef(type='string **', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(string &x, string *&y)',
            name='call_get_mappedtype_ref',
            items=[ParamDef(type='string &', name='x', out=True),
                   ParamDef(type='string *&', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(CtorsClass *x, CtorsClass **y)',
            name='call_get_wrappedtype_ptr',
            items=[ParamDef(type='CtorsClass *', name='x', out=True),
                   ParamDef(type='CtorsClass **', name='y')]))
        c.addItem(MethodDef(
            type='void', argsString='(CtorsClass &x, CtorsClass *&y)',
            name='call_get_wrappedtype_ref',
            items=[ParamDef(type='CtorsClass &', name='x', out=True),
                   ParamDef(type='CtorsClass *&', name='y')]))
        module.addItem(c)

        c = ClassDef(name='MappedTypeClass')
        c.addItem(MethodDef(
            type='string', argsString='()', name='get_name', isVirtual=True))
        c.addItem(MethodDef(
            type='string', argsString='()', name='call_get_name'))
        c.addItem(MethodDef(
            type='string', argsString='(string *s, int len)',
            name='concat', isVirtual=True, items=[
                ParamDef(type='string *', name='s', array=True),
                ParamDef(type='int', name='len', arraySize=True)]))
        c.addItem(MethodDef(
            type='string', argsString='(string *s, int len)',
            name='call_concat', items=[
                ParamDef(type='string *', name='s', array=True),
                ParamDef(type='int', name='len', arraySize=True)]))
        c.addItem(MemberVarDef(
            type='string', name='m_name'))
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

        gen1 = cffi_bindgen.CffiModuleGenerator(module.name,
                                                str(cls.tmpdir.join('%s.def')))

        module = ModuleDef('bindgen_test', '_extra', '_extra')
        module.addImport('_core')
        module.addPyCode('from _extra import *', 0)

        module.addItem(FunctionDef(
            type='SmartVector', argsString='(SmartVector &v)',
            name='double_vector', pyName='double_smart_vector', items=[
                ParamDef(type='SmartVector &', name='v')]))
        module.addItem(FunctionDef(
            type='Vector', argsString='(Vector &v)',
            name='double_mapped_vector', pyName='double_mapped_vector', items=[
                ParamDef(type='Vector &', name='v')]))

        c = ClassDef(name='ExternalModuleSubclass', bases=['SimpleClass'])
        module.addItem(c)

        mod_path = cls.tmpdir.join('%s.def' % module.name)
        with mod_path.open('w') as f:
            pickle.dump(module, f)

        gen2 = cffi_bindgen.CffiModuleGenerator(module.name,
                                                str(cls.tmpdir.join('%s.def')))
        gens = {'_core': gen1, '_extra': gen2}
        gen1.init(gens)
        gen2.init(gens)
        return gens

    @classmethod
    def build_module(cls, name):
        cpp_path = cls.tmpdir.join(name + '.cpp')
        h_path = cls.tmpdir.join(name + '.h')
        py_path = cls.tmpdir.join(name + '.py')
        user_py_path = cls.tmpdir.join(name.strip('_') + '.py')

        test_dir = os.path.dirname(__file__)
        sources = [str(cpp_path), os.path.join(test_dir, 'test_bindgen.cpp')]
        include_dirs = [test_dir, INCLUDES_DIR]
        tmpdir = str(cls.tmpdir)

        with cpp_path.open('w') as cpp_file, py_path.open('w') as py_file,\
             user_py_path.open('w') as user_py_file, h_path.open('w') as h_file:
            # Use distutis via cffi to build the cpp code
            cls.gens[name].writeFiles(
                py_file, cpp_file, h_file, user_py_file,
                'sources=["%s"], include_dirs=["%s"], tmpdir="%s"' %
                ('", "'.join(sources), '", "'.join(include_dirs), tmpdir))

        return user_py_path.pyimport()

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
        assert self.mod.global_cppmethod(4, 4) == 2

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
        obj = self.mod.CtorsClass(4)
        assert obj.cppmethod() == 8

        obj = self.mod.CtorsClass('a')
        assert obj.get() == ord('a')

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
        from_nocopy_cref = self.mod.ReturnWrapperClass.new_by_nocopy_cref(5)

        assert from_value.get() == 3
        assert from_ptr.get() == 4
        assert from_ref.get() == 5
        assert from_cref.get() == 5
        assert from_nocopy_cref.get() == 5

        assert not from_nocopy_cref._py_owned

        obj = self.mod.ReturnWrapperClass(15)
        from_value = obj.self_by_value()
        from_ptr = obj.self_by_ptr()
        from_ref = obj.self_by_ref()
        from_cref = obj.self_by_cref()
        from_nocopy_cref = obj.self_by_nocopy_cref()

        assert obj is not from_value
        assert obj is from_ptr
        assert obj is from_ref
        assert obj is not from_cref
        assert obj is from_nocopy_cref

        assert obj._py_owned
        assert from_value._py_owned
        assert from_cref._py_owned

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

    def test_operators(self):
        obj = self.mod.OperatorsClass(10, 10)
        obj += self.mod.OperatorsClass(2, 1)
        assert obj.x == 12
        assert obj.y == 11

        obj -= self.mod.OperatorsClass(20, 3)
        assert obj.x == -8
        assert obj.y == 8

    def test_pyint(self):
        obj = self.mod.PyIntClass()
        assert obj.noPyInt('c') == 'c'
        assert obj.onReturn('c') == ord('c')
        assert obj.onParameter(10) == chr(10)
        assert obj.onBoth(10) == 10

        assert obj.overloaded() == ord('c')
        assert obj.overloaded(11) == 11

    def test_array(self):
        AC = self.mod.ArrayClass

        objs = [AC(1), AC(2), AC(3)]
        assert AC.sum(objs) == 6

    def test_mappedtype(self):
        assert self.mod.std_string_len("Test") == 4
        assert self.mod.std_string_len(["Test", "Two"]) == 7

        class MappedTypeSubclass(self.mod.MappedTypeClass):
            def get_name(self):
                return "new name"

        obj = self.mod.MappedTypeClass()
        obj.m_name = "name"
        assert obj.m_name == "name"
        assert obj.m_name == obj.get_name()
        assert obj.m_name == obj.call_get_name()
        assert obj.concat(['10', '20']) == '1020'

        obj = MappedTypeSubclass()
        assert obj.call_get_name() == 'new name'

    def test_virtual_array(self):
        class ArraySubclass(self.mod.ArrayClass):
            def sum_virt(self, objs):
                return sum([-i.m_i for i in objs])

        class MappedTypeSubclass(self.mod.MappedTypeClass):
            def concat(self, obj):
                return ''.join(reversed(obj))

        obj = MappedTypeSubclass()
        assert obj.call_concat(['10', '20']) == '2010'

        AC = ArraySubclass
        obj = ArraySubclass()
        objs = [AC(1), AC(2), AC(3)]
        assert obj.call_sum_virt(objs) == -6

    def test_out_parameter(self):
        obj = self.mod.OutClass()
        a, b, c = obj.get_coords_ptr()
        assert a == 9
        assert b == 3
        assert c == 6

        a, b, c = obj.get_coords_ref()
        assert a == 9
        assert b == 3
        assert c == 6

        a, b = obj.get_wrappedtype_ptr()
        assert a.get() == 15
        assert b.get() == 30

        a, b = obj.get_wrappedtype_ref()
        assert a.get() == 45
        assert b.get() == 60

        a, b = obj.get_mappedtype_ptr()
        assert a == "15"
        assert b == "30"

        a, b = obj.get_mappedtype_ref()
        assert a == "45"
        assert b == "60"

    def test_inout_parameter(self):
        obj = self.mod.InOutClass()
        assert obj.double_ptr(10.0) == 20
        assert obj.double_ref(11) == 22

        assert obj.double_ptr(self.mod.CtorsClass(10.0)).get() == 20
        assert obj.double_ref(self.mod.CtorsClass(11)).get() == 22

        assert obj.double_ptr(self.mod.CtorsClass(10.0)).get() == 20
        assert obj.double_ref(self.mod.CtorsClass(11)).get() == 22

        assert obj.double_ptr((1, 2)) == (2, 4)
        assert obj.double_ref((4, 8)) == (8, 16)

    def test_virtual_ou(self):
        class OutSubclass(self.mod.OutClass):
            def get_coords_ptr(self):
                return (1, 2, 3)

            def get_coords_ref(self):
                return (4, 5, 6)

            def get_mappedtype_ptr(self):
                return ("by", "ptr")

            def get_mappedtype_ref(self):
                return ("via", "ref")

            def get_wrappedtype_ptr(self_):
                return (self.mod.CtorsClass(-1), self.mod.CtorsClass(-2))

            def get_wrappedtype_ref(self_):
                return (self.mod.CtorsClass(-3), self.mod.CtorsClass(-4))

        obj = OutSubclass()
        a, b, c = obj.call_get_coords_ptr()
        assert a == 1
        assert b == 2
        assert c == 3

        a, b, c = obj.call_get_coords_ref()
        assert a == 4
        assert b == 5
        assert c == 6

        a, b = obj.call_get_wrappedtype_ptr()
        assert a.get() == -1
        assert b.get() == -2

        a, b = obj.call_get_wrappedtype_ref()
        assert a.get() == -3
        assert b.get() == -4

        a, b = obj.call_get_mappedtype_ptr()
        assert a == "by"
        assert b == "ptr"

        a, b = obj.call_get_mappedtype_ref()
        assert a == "via"
        assert b == "ref"

    def test_virtual_inout(self):
        class InOutSubclass(self.mod.InOutClass):
            def double_ptr(self_, obj):
                import numbers
                if isinstance(obj, numbers.Number):
                    return -obj
                if isinstance(obj, tuple):
                    return (-obj[0], -obj[1])
                if isinstance(obj, self.mod.CtorsClass):
                    obj = self.mod.CtorsClass(-obj.get())
                    return obj

            def double_ref(self_, obj):
                import numbers
                if isinstance(obj, numbers.Number):
                    return -obj
                if isinstance(obj, tuple):
                    return (-obj[0], -obj[1])
                if isinstance(obj, self.mod.CtorsClass):
                    obj = self.mod.CtorsClass(-obj.get())
                    return obj

        obj = InOutSubclass()
        assert obj.call_double_ptr(10.0) == -10
        assert obj.call_double_ref(11) == -11

        assert obj.call_double_ptr(self.mod.CtorsClass(10.0)).get() == -10
        assert obj.call_double_ref(self.mod.CtorsClass(11)).get() == -11

        assert obj.call_double_ptr(self.mod.CtorsClass(10.0)).get() == -10
        assert obj.call_double_ref(self.mod.CtorsClass(11)).get() == -11

        assert obj.call_double_ptr((1, 2)) == (-1, -2)
        assert obj.call_double_ref((4, 8)) == (-4, -8)

    def test_trivial_mappedtype(self):
        class IntWrapperSubclass(self.mod.IntWrapperClass):
            def trivial_mappedtype(self, i):
                return (10, i - 1)

            def trivial_inout_mappedtype(self, i, k):
                return (10 + i, k - 1)

        obj = self.mod.IntWrapperClass()
        obj.trivial_mappedtype(10) == (9, 100)
        obj.trivial_inout_mappedtype(10, 9) == (9, 900)

        obj = IntWrapperSubclass()
        obj.trivial_mappedtype(10) == (10, 9)
        obj.call_trivial_mappedtype(10) == (10, 9)
        obj.trivial_inout_mappedtype(10, 9) == (11, 8)
        obj.call_trivial_inout_mappedtype(10, 9) == (11, 8)

    def test_abstract_class(self):
        with pytest.raises(TypeError):
            self.mod.AbstractClass()
        self.mod.ConcreteSubclass()

        class PyAbstractSubClass(self.mod.AbstractClass):
            pass

        with pytest.raises(TypeError):
            PyAbstractSubClass()

    def test_purevirtual_abstract_class(self):
        with pytest.raises(TypeError):
            self.mod.PureVirtualClass()

        class PureVirtualSubclass(self.mod.PureVirtualClass):
            pass

        with pytest.raises(NotImplementedError):
            PureVirtualSubclass().purevirtual()

        class PureVirtualSubclass(self.mod.PureVirtualClass):
            def purevirtual(self):
                return 42

        assert PureVirtualSubclass().call_purevirtual() == 42

    def test_custom_conversion_class(self):
        vec = self.mod.SmartVector((2, 4))
        assert vec.x == 2
        assert vec.y == 4

        other_vec = self.mod.double_vector(vec)
        assert other_vec.x == 4
        assert other_vec.y == 8

    def test_allownone(self):
        obj = self.mod.AllowNoneClass()
        with pytest.raises(TypeError):
            obj.get_addr_ref(None)
        assert obj.get_addr_ptr(None) == 0

        assert obj.allow_none_get_addr_ref(None) != 0
        assert obj.allow_none_get_addr_ptr(None) != 0

        obj = self.mod.AllowNoneSmartVector(None)
        assert obj.x == -1
        assert obj.y == -1

    def test_keep_reference(self):
        keeping_obj = self.mod.KeepReferenceClass()
        kept_obj1 = self.mod.KeepReferenceClass()
        kept_obj2 = self.mod.KeepReferenceClass()

        wr1 = weakref.ref(kept_obj1)
        wr2 = weakref.ref(kept_obj2)
        keeping_obj.keep_ref(kept_obj1)
        keeping_obj.keep_ref2(kept_obj2)

        del kept_obj1
        del kept_obj2
        gc.collect()
        assert wr1() is not None
        assert wr2() is not None

        del keeping_obj
        gc.collect()
        assert wr1() is None
        assert wr2() is None

        kept_obj = self.mod.KeepReferenceClass()
        wr = weakref.ref(kept_obj)
        self.mod.global_keep_ref(kept_obj)

        del kept_obj
        gc.collect()
        assert wr() is not None

        self.mod.global_keep_ref(self.mod.KeepReferenceClass())
        gc.collect()
        assert wr() is not None

    def test_transfer_param(self):
        parent = self.mod.TransferClass()
        child = self.mod.TransferClass()
        wr = weakref.ref(child)
        parent.transfer_param(child)

        del child
        gc.collect()
        assert wr() is not None

        del parent
        gc.collect()
        assert wr() is None


        obj = self.mod.TransferClass()
        wr = weakref.ref(obj)
        self.mod.TransferClass.static_transfer_param(obj)
        assert not obj._py_owned

        del obj
        gc.collect()
        assert wr() is None


        obj = self.mod.TransferClass()
        wr = weakref.ref(obj)
        self.mod.global_transfer_param(obj)
        assert not obj._py_owned

        del obj
        gc.collect()
        assert wr() is None

    def test_transfer_return(self):
        parent = self.mod.TransferClass()
        child = self.mod.TransferClass()
        wr = weakref.ref(child)
        parent.transfer_return(child)

        del child
        gc.collect()
        assert wr() is not None

        del parent
        gc.collect()
        assert wr() is None

        # This Ctor is annotated with Transfer
        obj = self.mod.TransferClass(10)
        assert not obj._py_owned
        wr = weakref.ref(obj)

        # Transfer on Ctors is a special case: the object is kept alive even
        # after the last reference in user code is gone
        del obj
        gc.collect()
        assert wr() is not None

        # Don't test static methods or global functions, they can't have the
        # Transfer annotation

    def test_transferback_param(self):
        functions = [self.mod.TransferClass().transferback_param,
                     self.mod.TransferClass.static_transferback_param,
                     self.mod.global_transferback_param]
        for f in functions:
            obj = self.mod.TransferClass()
            wr = weakref.ref(obj)
            wrapper_lib.give_ownership(obj)
            f(obj)

            del obj
            gc.collect()
            assert wr() is None

    def test_transferback_return(self):
        functions = [self.mod.TransferClass().transferback_return,
                     self.mod.TransferClass.static_transferback_return,
                     self.mod.global_transferback_return]
        for f in functions:
            obj = self.mod.TransferClass()
            wr = weakref.ref(obj)
            wrapper_lib.give_ownership(obj)
            obj = f(obj)

            del obj
            gc.collect()
            assert wr() is None

    def test_transferthis_param(self):
        obj = self.mod.TransferClass(None)
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is None


        owner = self.mod.TransferClass()
        obj = self.mod.TransferClass(owner)
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is not None
        del owner
        gc.collect()
        assert wr() is None


        obj = self.mod.TransferClass()
        obj.transferthis_param(None)
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is None


        owner = self.mod.TransferClass()
        obj = self.mod.TransferClass()
        obj.transferthis_param(owner)
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is not None
        del owner
        gc.collect()
        assert wr() is None

    def test_transferthis_return(self):
        obj = self.mod.TransferClass()
        wr = weakref.ref(obj)
        obj.transferthis_return()
        assert not obj._py_owned

        del obj
        gc.collect()
        assert wr() is None

    def test_transfer_array(self):
        obj = self.mod.TransferClass()
        obj.transfer_array([obj, self.mod.TransferClass()])
        obj.transfer_array([(10, 10), (8, 8)])

    def test_factory(self):
        obj = self.mod.FactoryClass().make()
        assert obj._py_owned

    def test_factory_keepreference(self):
        keptobj = self.mod.FactoryClass()
        obj = self.mod.FactoryClass().make_keep_ref(keptobj)
        wr = weakref.ref(keptobj)

        del keptobj
        gc.collect()
        assert wr() is not None

        del obj
        gc.collect()
        assert wr() is None

    def test_factory_transferthis(self):
        owner = self.mod.FactoryClass()
        obj = self.mod.FactoryClass().make_transfer_this(owner)
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is not None

        del owner
        gc.collect()
        assert wr() is None

    def test_factory_virtual(self):
        class FactorySubclass(self.mod.FactoryClass):
            def make(self):
                newobj = FactorySubclass()
                return newobj

        obj = FactorySubclass().call_make()
        assert not obj._py_owned
        wr = weakref.ref(obj)

        del obj
        gc.collect()
        assert wr() is not None

    def test_deprecated(self):
        obj = pytest.deprecated_call(self.mod.DeprecatedClass)
        pytest.deprecated_call(obj.deprecated_method)
        pytest.deprecated_call(self.mod.deprecated_func)

    def test_second_module(self):
        obj = self.mod2.double_smart_vector((1, 2))
        assert obj.x == 2
        assert obj.y == 4

        obj = self.mod2.double_mapped_vector((2, 4))
        assert obj == (4, 8)

        obj = self.mod2.ExternalModuleSubclass()
        assert obj.simple_method(1.1) == 1

    def test_virtualcatchercode(self):
        class VirtualCatcherClass(self.mod.VirtualCatcherBase):
            def vmeth(self):
                return 'test'

        obj = VirtualCatcherClass()
        assert obj.call_vmeth() == 'TEST'
