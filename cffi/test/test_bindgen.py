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
from etgtools import extractors
from etgtools.generators import nci
from etgtools.extractors import (
    ModuleDef, DefineDef, ClassDef, MethodDef, FunctionDef, ParamDef,
    CppMethodDef, CppMethodDef_cffi, MemberVarDef, GlobalVarDef, PyPropertyDef,
    PyFunctionDef, PyClassDef, PyCodeDef, EnumDef, EnumValueDef, TypedefDef,
    MappedTypeDef_cffi, ArgsString)

from etgtools.cffi_generator import CffiWrapperGenerator
from etgtools.cffi.bindgen import BindingGenerator, LiteralVerifyArg

from buildtools.config import Config
cfg = Config(noWxConfig=True).ROOT_DIR
INCLUDES_DIR = os.path.join(cfg, 'cffi', 'include')

class TestBindGen(object):
    @classmethod
    def setup_class(cls):
        # Make sure the extractors uses the cffi backend
        sys.argv.append('--cffi')

        cls.tmpdir = pytest.ensuretemp('build', dir=True)
        cls.gen = cls.create_generators()
        cls.mod = cls.build_module('_core')
        cls.mod2 = cls.build_module('_extra')

    @classmethod
    def create_generators(cls):
        gen = BindingGenerator(str(cls.tmpdir.join('%s.def')))

        module = ModuleDef('bindgen_test', '_core', '_core')
        module.addHeaderCode('#include <test_bindgen.h>')

        module.addPyCode('from _core import *', 0)
        module.addPyCode('import _core', 0)

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

        f = FunctionDef(
            type='double', argsString='()',
            name='custom_code_global_func', pyName='custom_code_global_func')
        f.setCppCode("return custom_code_global_func() - 1;")
        module.addItem(f)

        f = FunctionDef(
            type='double', argsString='(CtorsClass c, IntWrapper i)',
            name='custom_code_global_func_wrappertypes', pyName='custom_code_global_func_wrappertypes',
            items=ArgsString('(CtorsClass &c, IntWrapper i)'))
        f.setCppCode("return c->get() + i->i;")
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
        c.addMethod('int', 'simple_method', '(double f)')
        module.addItem(c)

        module.addItem(ClassDef(name='SimpleSubclass', bases=['SimpleClass']))

        c = ClassDef(name='VMethClass')
        c.addMethod('int', 'virtual_method', '(int i)', isVirtual=True)
        c.addMethod('int', 'call_virtual', '(int i)')
        c.addMethod('int', 'overridden_vmeth1', '()', isVirtual=True)
        c.addMethod('int', 'call_overridden_vmeth1', '()')
        c.addMethod('VMethClass*', 'overridden_vmeth2', '()', isVirtual=True)
        c.addMethod('VMethClass*', 'call_overridden_vmeth2', '()')
        c.addMethod('IntWrapper', 'overridden_vmeth3', '(int i)', isVirtual=True)
        c.addMethod('IntWrapper', 'call_overridden_vmeth3', '(int i)')
        c.addItem(CppMethodDef_cffi(
            'unoverridden_cppvmeth', isVirtual=True,
            pyArgs=ArgsString('WL_Self self, char somechar'),
            pyBody='return call(wrapper_lib.get_ptr(self), somechar)',

            cReturnType='char', cArgsString='(void *self, char i)',
            cBody='return \'a\' + static_cast<VMethClass*>(self)->unoverridden_cppvmeth(i - \'a\');',

            originalCppType='int',
            originalCppArgs=ArgsString('(int i)'),

            virtualCReturnType='int',
            virtualCArgsString='(void *self, int i)',
            virtualCBody='return call(this, i);',

            virtualPyArgs='(self, i)',
            virtualPyBody="""\
            c = chr(ord('a') + i)
            res = wrapper_lib.obj_from_ptr(self).unoverridden_cppvmeth(c)
            return ord(res) - ord('a')
            """,
        ))
        c.addItem(CppMethodDef_cffi(
            'call_unoverridden_cppvmeth',
            pyArgs=ArgsString('WL_Self self, char somechar'),
            pyBody='return call(wrapper_lib.get_ptr(self), somechar)',
            cReturnType='char', cArgsString='(void *self, char i)',
            cBody='return \'a\' + static_cast<VMethClass*>(self)->call_unoverridden_cppvmeth(i - \'a\');',
        ))
        module.addItem(c)

        module.addItem(TypedefDef(type='int', name='IntAlias'))

        c = ClassDef(name='VMethSubclass', bases=['VMethClass'])
        c.addMethod('int', 'overridden_vmeth1', '()', isVirtual=True)
        c.addMethod('VMethSubclass*', 'overridden_vmeth2', '()', isVirtual=True)
        c.addMethod('IntWrapper', 'overridden_vmeth3', '(IntAlias i)',
                    isVirtual=True)
        module.addItem(c)

        c = ClassDef(name='PVMethClass')
        c.addMethod('int', 'protected_virtual_method', '(int i)',
                    protection='protected', isVirtual=True)
        c.addMethod('int', 'call_method', '(int i)')
        module.addItem(c)

        c = ClassDef(name='OverloadedVMethClass')
        c.addMethod('int', 'overloaded_vmeth', '()', isVirtual=True)
        c.addMethod('int', 'overloaded_vmeth', '(int x)', isVirtual=True)
        c.addMethod('int', 'call_overloaded_vmeth', '()')
        c.addMethod('int', 'call_overloaded_vmeth', '(int x)')
        module.addItem(c)

        c = ClassDef(name='OverloadedVMethSubclass',
                     bases=['OverloadedVMethClass'])
        module.addItem(c)

        c = ClassDef(name='PrivateVMethBase')
        c.addMethod('int', 'pvmeth', '()', isVirtual=True, isPureVirtual=True)
        c.addMethod('int', 'call_pvmeth', '()')
        module.addItem(c)

        c = ClassDef(name='PrivateVMethClass1', bases=['PrivateVMethBase'])
        c.addMethod('int', 'pvmeth', '()', isVirtual=True, protection='private')
        module.addItem(c)

        c = ClassDef(name='PrivateVMethClass2', bases=['PrivateVMethBase'])
        c.addMethod('int', 'pvmeth', '()', isVirtual=True, protection='private')
        c.addMethod('int', 'pvmeth', '(int x)', isVirtual=True)
        module.addItem(c)

        c = ClassDef(name='PMethClass')
        c.addMethod('char', 'protected_method', '(char c)',
                    protection='protected')
        c.addMethod('int', 'static_protected_method', argsString='()',
                    protection='protected', isStatic=True)

        module.addItem(c)

        module.addItem(TypedefDef(type='CtorsClass', name='CtorsAlias'))

        c = ClassDef(name='CtorsClass')
        c.addMethod('', 'CtorsClass', '()', isCtor=True)
        c.addMethod('', 'CtorsClass', '(const CtorsClass &other)', isCtor=True)
        c.addMethod('', 'CtorsClass', '(int i)', isCtor=True)

        c.addMethod('int','get',  '()')
        m = MethodDef(
            type='double', argsString='(double f)',
            name='custom_code_meth', pyName='custom_code_meth',
            items=[ParamDef(type='double', name='f')])
        m.setCppCode('return self->get() * f;')
        c.addCppCtor('(char a)', 'return new CtorsClass((int)a);')
        c.addCppMethod('double', 'cppmethod', '()', 'return self->get() * 2;')
        c.addCppMethod('double', 'static_cppmethod', '()', 'return 1.0;',
                       isStatic=True)
        c.addPyMethod('double_i', '(self)', 'return self.get() * 2')
        c.addItem(m)

        module.addItem(c)

        c = ClassDef(name='PCtorClass')
        c.addMethod('', 'PCtorClass', '(int i)', protection='protected',
                    isCtor=True)
        c.addMethod('int', 'get', '()')
        module.addItem(c)

        c = ClassDef(name='PrivateCopyCtorClass')
        c.addPrivateCopyCtor()
        module.addItem(c)

        c = ClassDef(name='PrivateCopyCtorSubclass',
                     bases=['PrivateCopyCtorClass'])
        module.addItem(c)

        c = ClassDef(name='ReturnWrapperClass')
        c.addMethod('', 'ReturnWrapperClass', '(int i)', isCtor=True)
        c.addMethod('int', 'get', '()')
        c.addMethod('ReturnWrapperClass', 'new_by_value', '(int i)',
                    isStatic=True)
        c.addMethod('ReturnWrapperClass *', 'new_by_ptr', '(int i)',
                    isStatic=True)
        c.addMethod('ReturnWrapperClass &', 'new_by_ref', '(int i)',
                    isStatic=True)
        c.addMethod('const ReturnWrapperClass &', 'new_by_cref', '(int i)',
                    isStatic=True)
        c.addMethod('const ReturnWrapperClass &', 'new_by_nocopy_cref', '(int i)',
                    isStatic=True, noCopy=True)
        c.addMethod('ReturnWrapperClass', 'self_by_value', '()')
        c.addMethod('ReturnWrapperClass *', 'self_by_ptr', '()')
        c.addMethod('ReturnWrapperClass &', 'self_by_ref', '()')
        c.addMethod('const ReturnWrapperClass &', 'self_by_cref', '()')
        c.addMethod('const ReturnWrapperClass &', 'self_by_nocopy_cref', '()',
                    noCopy=True)
        module.addItem(c)

        c = ClassDef(name='PrivateCCtorReturnWrapperClass')
        c.addMethod('', 'PrivateCCtorReturnWrapperClass', '(int i)',
                    isCtor=True)
        c.addPrivateCopyCtor()
        c.addMethod(
            'const PrivateCCtorReturnWrapperClass &', 'self_by_cref', '()')
        c.addMethod(
            'const PrivateCCtorReturnWrapperClass &', 'new_by_cref', '(int i)',
            isStatic=True)
        c.addMethod('int', 'get', '()')
        module.addItem(c)

        c = ClassDef(name='VDtorClass')
        c.addMethod('', '~VDtorClass', '()', isVirtual=True, isDtor=True)
        c.addMethod('void', 'delete_self', '()')

        module.addItem(c)

        c = ClassDef(name='VDtorSubclass', bases=['VDtorClass'])
        c.addMethod('', '~VDtorSubclass', '()', isVirtual=True, isDtor=True)
        module.addItem(c)

        c = ClassDef(name='VDtorSubSubclass', bases=['VDtorSubclass'])
        module.addItem(c)

        c = ClassDef(name='PDtorClass')
        c.addDtor('private')
        module.addItem(c)

        c = ClassDef(name='MemberVarClass')
        c.addMethod('', 'MemberVarClass', '(int i)', isCtor=True)
        c.addMethod('int', 'Get_i', '()')
        c.addMethod('void', 'Set_i', '(int i)')
        c.addPyMethod('Get_i_pymeth', '(self)', 'return self._i')
        c.addPyMethod('Set_i_pymeth', '(self, i)', 'self._i = i')
        c.addItem(MemberVarDef(type='int', name='m_i', pyName='m_i'))

        c.addAutoProperties()
        module.addItem(c)

        c = ClassDef(name='NestedClassReturnDependant')
        c.addMethod('NestedClassesOuter::NestedClassesInner', 'get', '()')
        module.addItem(c)

        c = ClassDef(name='NestedClassArgDependant')
        c.addMethod(
            'int', 'get', '(const NestedClassesOuter::NestedClassesInner &i)')
        module.addItem(c)

        c = ClassDef(name='NestedClassesOuter')
        ic = ClassDef(name='NestedClassesInner')
        ic2 = ClassDef(name='NestedClassesInnerVirtual')
        c.innerclasses = [ic, ic2]
        ic.addMethod('int', 'vmeth', '()', isVirtual=True)
        ic.addMethod('int', 'call_vmeth', '()')
        ic.addItem(MemberVarDef(type='int', name='m_i', pyName='m_i'))
        ic.addPyMethod(
            type='int', argsString='(self)', name='Getpyi',
            body='return self.m_i')
        ic.addPyMethod(
            type='void', argsString='(self, i)', name='Setpyi',
            body='self.m_i = i')
        ic.addMethod('int', 'Get_i', '()')
        ic.addMethod('void', 'Set_i', '(int i)')
        ic.addMethod('void', 'overloaded', '()')
        ic.addMethod('void', 'overloaded', '(double f)')

        ic.addAutoProperties()

        ic2.addMethod(
            'NestedClassesInnerVirtual *', 'make', '()', isVirtual=True)
        module.addItem(c)

        c = ClassDef(name='DefaultsClass')
        c.addItem(EnumDef(name='DefaultsEnum', items=[
            EnumValueDef(name='Defaults_A'),
            EnumValueDef(name='Defaults_B')]))
        c.addMethod(
            'int', 'defaults_enum', '(DefaultsEnum i = Defaults_A)')
        c.addMethod(
            'int', 'defaults_array',
             ArgsString('(int len=0, IntWrapper *a=NULL)')
            .annt(0, 'arraySize').annt(1, 'array'))
        c.addMethod(
            'int', 'defaults_meth',
             '(const char * s = other_global_str, const IntWrapper &i = IntWrapper(4), const CtorsClass &c = CtorsClass(6))')
        module.addItem(c)

        c = ClassDef(name='InheritedDefaultsClass', bases=['DefaultsClass'])
        c.addMethod(
            'int', 'inherited_defaults_method', '(DefaultsEnum i = Defaults_A)')
        module.addItem(c)

        c = ClassDef(name='OperatorsClass')
        c.addMethod('', 'OperatorsClass', '(int x, int y)', isCtor=True)
        c.addMethod('OperatorsClass &', 'operator+=', '(OperatorsClass &rhs)')
        c.addMethod('OperatorsClass &', 'operator-=', '(OperatorsClass &rhs)')
        c.addMethod('OperatorsClass', 'operator-', '()')
        c.addItem(MemberVarDef(name='x', type='int'))
        c.addItem(MemberVarDef(name='y', type='int'))
        module.addItem(c)

        c = ClassDef(name='ClassWithEnum')
        c.addItem(EnumDef(name='BOOLEAN', items=[
            EnumValueDef(name='BOOL_TRUE'),
            EnumValueDef(name='BOOL_FALSE')]))
        c.addMethod('BOOLEAN', 'flip', '(BOOLEAN b)', isVirtual=True)
        c.addMethod('', '~ClassWithEnum', '()', isDtor=True, isVirtual=True)
        module.addItem(c)

        c = ClassDef(name='PyIntClass')
        c.addMethod('char', 'noPyInt', '(char c)')
        c.addMethod('char', 'onReturn', '(char c)', pyInt=True)
        c.addMethod('char', 'onParameter', ArgsString('(char c)')
                                           .annt(0, 'pyInt'))
        c.addMethod('char', 'onBoth',
                    ArgsString('(char c)').annt(0, 'pyInt'), pyInt=True)
        c.addMethod('char', 'overloaded', '()', pyInt=True)
        c.addMethod('char', 'overloaded',
                    ArgsString('(char c)').annt(0, 'pyInt'), pyInt=True)
        module.addItem(c)

        module.addItem(TypedefDef(type='char', name='CharTypedef'))

        c = ClassDef(name='CharTypesClass')
        c.addMethod('int', 'char_scalar', '(char i)')
        c.addMethod('int', 'schar_scalar', '(signed char iii)')
        c.addMethod('int', 'uchar_scalar', '(unsigned char i)')
        c.addMethod('int', 'char_vector', '(char *i)')
        c.addMethod('int', 'schar_vector', '(signed char *i)')
        c.addMethod('int', 'uchar_vector', '(unsigned char *i)')
        c.addMethod('wchar_t *', 'wchar_string', '(wchar_t *i)')
        c.addMethod('CharTypedef *', 'typedef_string', '(CharTypedef *i)')
        module.addItem(c)

        c = ClassDef(name='NestedTypedefsClass')
        c.addItem(TypedefDef(type='int', name='int1'))
        c.addItem(TypedefDef(type='int1', name='int2'))
        c.addMethod('int2', 'return_typedef', '(int2 i)')
        module.addItem(c)

        c = ClassDef(name='UnsignedTypesClass')
        c.addMethod('unsigned', 'u', '(unsigned i)')
        c.addMethod('unsigned int', 'ui', '(unsigned int i)')
        c.addMethod('unsigned long long', 'ull', '(unsigned long long i)')
        module.addItem(c)

        c = ClassDef(name='ArrayClass')
        c.addMethod('', 'ArrayClass', '()', isCtor=True)
        c.addMethod('', 'ArrayClass', '(int i)', isCtor=True)
        c.addMethod(
            'int', 'sum', ArgsString('(ArrayClass *objs, int len)')
                          .annt(0, 'array').annt(1, 'arraySize'),
            isStatic=True)
        c.addMethod(
            'int', 'sum_virt', ArgsString('(ArrayClass *objs, int len)')
                               .annt(0, 'array').annt(1, 'arraySize'),
            isVirtual=True)
        c.addMethod(
            'int', 'call_sum_virt',  ArgsString('(ArrayClass *objs, int len)')
                                    .annt(0, 'array').annt(1, 'arraySize'))
        c.addMethod(
            'int', 'sum_mapped_type', ArgsString( '(Vector *objs, int len)')
                                      .annt(0, 'array').annt(1, 'arraySize'),
            isStatic=True)
        c.addItem(MemberVarDef(type='int', name='m_i'))
        module.addItem(c)

        c = ClassDef(name='InOutClass')
        c.addMethod(
            'void', 'double_ptr', ArgsString('(int *num)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_ptr', ArgsString('(CtorsClass * num)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_ptr', ArgsString('(Vector * vec)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_ref', ArgsString('(int & num)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_ref', ArgsString('(CtorsClass & num)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_ref', ArgsString('(Vector & vec)').annt(0, 'inOut'),
            isVirtual=True)
        c.addMethod(
            'void', 'double_refptr',
             ArgsString('(CtorsClass *& num)').annt(0, 'inOut'), isVirtual=True)
        c.addMethod('void', 'double_refptr', isVirtual=True,
                    argsString=ArgsString('(Vector *& vec)').annt(0, 'inOut'))
        c.addMethod('void', 'double_ptrptr', isVirtual=True,
                    argsString=ArgsString('CtorsClass ** num)').annt(0, 'inOut'))
        c.addMethod('void', 'double_ptrptr', isVirtual=True,
                    argsString=ArgsString('Vector ** vec)').annt(0, 'inOut'))

        c.addMethod('void', 'call_double_ptr',
                    ArgsString('(int * num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ptr',
                    ArgsString('(CtorsClass * num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ptr',
                    ArgsString('(Vector * vec)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ref',
                    ArgsString('(int & num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ref',
                    ArgsString('(CtorsClass & num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ref',
                    ArgsString('(Vector & vec)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_refptr',
                    ArgsString('CtorsClass *& num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_refptr',
                    ArgsString('Vector *& vec)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ptrptr',
                    ArgsString('CtorsClass ** num)').annt(0, 'inOut'))
        c.addMethod('void', 'call_double_ptrptr',
                    ArgsString('Vector ** vec)').annt(0, 'inOut'))
        module.addItem(c)

        c = ClassDef(name='AllowNoneClass')
        c.addMethod('long', "get_addr_ptr", '(SmartVector *v)')
        c.addMethod('long', "get_addr_ref", '(SmartVector &v)')
        c.addMethod('long', "allow_none_get_addr_ptr",
                    '(AllowNoneSmartVector *v)')
        c.addMethod('long', "allow_none_get_addr_ref",
                    '(AllowNoneSmartVector &v)')
        module.addItem(c)

        c = ClassDef(name='AbstractClass', abstract=True)
        c.addMethod('AbstractClass*', 'get_instance', '()', isStatic=True,
                    factory=True)
        c.addMethod('void', 'virtual_meth', '()', isVirtual=True)
        module.addItem(c)

        module.addItem(ClassDef(name='ConcreteSubclass',
                                bases=['AbstractClass']))

        c = ClassDef(name="PureVirtualClass")
        c.addMethod('int', 'purevirtual', '()', isVirtual=True,
                    isPureVirtual=True)
        c.addMethod('int', 'call_purevirtual', '()')
        module.addItem(c)

        c = ClassDef(
            name='SmartVector',
            convertFromPyObject_cffi="""\
            return SmartVector(py_obj[0], py_obj[1])
            """,
            instanceCheck_cffi="""\
            import collections
            return isinstance(py_obj, collections.Sequence) and len(py_obj) == 2
            """)
        c.addMethod('', 'SmartVector', '(int x_, int y_)', isCtor=True)
        c.addItem(MemberVarDef(type='int', name='x'))
        c.addItem(MemberVarDef(type='int', name='y'))
        module.addItem(c)

        c = ClassDef(
            name='AllowNoneSmartVector',
            allowNone=True,
            convertFromPyObject_cffi="""\
            if py_obj is None:
                return AllowNoneSmartVector(-1, -1)
            return AllowNoneSmartVector(py_obj[0], py_obj[1])
            """,
            instanceCheck_cffi="""\
            import collections
            return isinstance(py_obj, collections.Sequence) and len(py_obj) == 2
            """)
        c.addMethod('', 'AllowNoneSmartVector', '(int x_, int y_)',
                    isCtor=True)
        c.addItem(MemberVarDef(type='int', name='x'))
        c.addItem(MemberVarDef(type='int', name='y'))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='SmartVector', argsString='(SmartVector &vec)',
            name='double_vector', items=[ParamDef(
                type='SmartVector &', name='vec')]))

        c = ClassDef(name='KeepReferenceClass')
        c.addMethod('void', 'keep_ref', ArgsString('(KeepReferenceClass &i)')
                                        .annt(0, 'keepReference'))
        c.addMethod('void', 'keep_ref2', ArgsString('(KeepReferenceClass &i)')
                                         .annt(0, 'keepReference'))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='void', argsString='(KeepReferenceClass &i)',
            name='global_keep_ref', items=[
                ParamDef(type='KeepReferenceClass &', name='i',
                        keepReference=True)]))

        c = ClassDef(name='TransferClass')
        c.addMethod('', 'TransferClass', '()', isCtor=True)
        c.addMethod('', 'TransferClass', '(int i)', isCtor=True, transfer=True)
        c.addMethod('', 'TransferClass',
                    ArgsString('(TransferClass * i)').annt(0, 'transferThis'),
                    isCtor=True)
        c.addMethod('void', "transfer_param",
                    ArgsString('(TransferClass *obj)').annt(0, 'transfer'))
        c.addMethod('void', "static_transfer_param",
                    ArgsString('(TransferClass *obj)').annt(0, 'transfer'),
                    isStatic=True)
        c.addMethod('TransferClass *', "transfer_return",
                    ArgsString('(TransferClass *obj)'), transfer=True)
        c.addMethod('void', "transferback_param",
                    ArgsString('(TransferClass *obj)').annt(0, 'transferBack'))
        c.addMethod('void', "transferthis_param",
                    ArgsString('(TransferClass *obj)').annt(0, 'transferThis'))
        c.addMethod('void', "transferthis_return", '()', transferThis=True)
        c.addMethod('void', "static_transferback_param",
                    ArgsString('(TransferClass *obj)').annt(0, 'transferBack'),
                    isStatic=True)
        c.addMethod('void', "transferback_return",
                    ArgsString('(TransferClass *obj)').annt(0, 'transferBack'))
        c.addMethod('TransferClass *', "static_transferback_return",
                   '(TransferClass *obj)', isStatic=True, transferBack=True,)
        c.addMethod('void', 'transfer_array',
                    ArgsString('(TransferClass *objs, int count)')
                    .annt(0, ('array', 'transfer')).annt(1, 'arraySize'))
        c.addMethod('void', 'transfer_array',
                    ArgsString('(Vector *objs, int count)')
                    .annt(0, ('array', 'transfer')).annt(1, 'arraySize'))
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
        c.addMethod('FactoryClass *', 'make', '()', factory=True, isVirtual=True)
        c.addMethod('FactoryClass *', 'call_make', '()')
        c.addMethod('FactoryClass *', 'make_keep_ref',
                    ArgsString('(FactoryClass *ref)').annt(0, 'keepReference'),
                    factory=True)
        c.addMethod('FactoryClass *', 'make_transfer_this',
                    ArgsString('(FactoryClass *ref)').annt(0, 'transferThis'),
                    factory=True)
        module.addItem(c)

        c = ClassDef(name='VirtualParametersOwnershipClass')
        c.addMethod(
            'void', 'by_value', '(CtorsClass i)',
            isVirtual=True, isPureVirtual=True)
        c.addMethod(
            'void', 'by_ptr', '(CtorsClass *i)',
            isVirtual=True, isPureVirtual=True)
        c.addMethod(
            'void', 'by_ref', '(CtorsClass &i)',
            isVirtual=True, isPureVirtual=True)
        c.addMethod(
            'void', 'by_cref', '(const CtorsClass &i)',
            isVirtual=True, isPureVirtual=True)
        c.addMethod(
            'void', 'by_cref_private_cctor', '(const PrivateCopyCtorClass &i)',
            isVirtual=True)
        c.addMethod('void', 'call_by_value', '()')
        c.addMethod('void', 'call_by_ptr', '()')
        c.addMethod('void', 'call_by_ref', '()')
        c.addMethod('void', 'call_by_cref', '()')
        c.addMethod('void', 'call_by_cref_private_cctor', '()')
        module.addItem(c)

        c = ClassDef(name="DeprecatedClass", deprecated=True)
        c.addMethod('void', 'deprecated_method', '()')
        module.addItem(c)

        module.addItem(FunctionDef(
            type='void', argsString='()', name='deprecated_func',
            deprecated=True))

        c = ClassDef(name='VirtualCatcherBase')
        c.addMethod(
            'const char*', 'vmeth', '()', isVirtual=True,
            virtualCatcherCode_cffi="""\
            res = self.vmeth()
            if not isinstance(res, str):
                return ""
            else:
                return res.upper()
            """)
        c.addMethod('const char*', 'call_vmeth', '()')
        module.addItem(c)

        module.addItem(MappedTypeDef_cffi(
            name='string', cType='char *',
            headerCode=["#include <string>\nusing std::string;"],
            py2c="""\
            l = len(py_obj)
            cdata = ffi.cast('char*', clib.malloc(l + 1))
            cdata[0:l] = py_obj
            cdata[l] = '\\0'
            return cdata""",
            c2py="""\
            ret = ffi.string(cdata)
            clib.free(cdata)
            return ret
            """,
            c2cpp="return new string(cdata);",
            cpp2c="""\
            char *cdata = (char*)malloc(cpp_obj->length() + 1);
            strcpy(cdata, cpp_obj->c_str());
            return cdata;""",
            instanceCheck='return isinstance(py_obj, (str, unicode))',))

        module.addItem(MappedTypeDef_cffi(
            name='Vector', cType='int *',
            py2c="""\
            array = ffi.cast('int*', clib.malloc(ffi.sizeof('int') * 2))
            array[0:2] = [int(py_obj[0]), int(py_obj[1])]
            return array""",
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
            instanceCheck="""\
            import collections
            return (isinstance(py_obj, collections.Sequence) and len(py_obj) >= 2 and
                    isinstance(py_obj[0], numbers.Number) and
                    isinstance(py_obj[1], numbers.Number))
            """,))

        module.addItem(MappedTypeDef_cffi(
            name='IntWrapper', cType='int',
            py2c="return int(py_obj)",
            c2py="return cdata",
            c2cpp="return new IntWrapper(cdata);",
            cpp2c="return cpp_obj->i;",
            instanceCheck="""\
            import numbers
            return isinstance(py_obj, numbers.Number)""",
            placeHolder='0'))

        module.addItem(MappedTypeDef_cffi(
            name='BrokenMappedType', cType='int',
            py2c="raise TypeError('Message')",
            c2py="",
            c2cpp="return new BrokenMappedType();",
            cpp2c="return 0;",
            instanceCheck="return True",
            placeHolder='0'))

        module.addItem(FunctionDef(
            type='void', name='take_broken_mapped_type',
            items=ArgsString('(BrokenMappedType b)')))

        module.addItem(FunctionDef(
            type='int', argsString='(string *str)', name='std_string_len',
            items=[ParamDef(name='str', type='string *')],
            overloads=[FunctionDef(
            type='int', argsString='(string *str), int len',
            name='std_string_len', items=[
                ParamDef(name='str', type='string *', array=True),
                ParamDef(name='len', type='int', arraySize=True)])]))

        c = ClassDef(name='IntWrapperClass')
        c.addMethod('IntWrapper', 'trivial_mappedtype',
                    ArgsString('(IntWrapper i, IntWrapper & k)').annt(1, 'out'),
                    isVirtual=True)
        c.addMethod('IntWrapper', 'call_trivial_mappedtype',
                    ArgsString('(IntWrapper i, IntWrapper & k)').annt(1, 'out'))
        c.addMethod('IntWrapper', 'trivial_inout_mappedtype',
                    ArgsString('(IntWrapper i, IntWrapper & k)').annt(1, 'inOut'),
                    isVirtual=True)
        c.addMethod('IntWrapper', 'call_trivial_inout_mappedtype',
                    ArgsString('(IntWrapper i, IntWrapper & k)').annt(1, 'inOut'))
        module.addItem(c)

        c = ClassDef(name='OutClass')
        c.addMethod('int', 'get_coords_ptr',
                    ArgsString('(int *x, int *y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('int', 'get_coords_ref',
                    ArgsString('(int &x, int &y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('void', 'get_mappedtype_ptr',
                    ArgsString('(string *x, string **y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('void', 'get_mappedtype_ref',
                    ArgsString('(string &x, string *&y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('void', 'get_wrappedtype_ptr',
                    ArgsString('(CtorsClass *x, CtorsClass **y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('void', 'get_wrappedtype_ref',
                    ArgsString('(CtorsClass &x, CtorsClass *&y)').annt(0, 'out'),
                    isVirtual=True)
        c.addMethod('int', 'call_get_coords_ptr',
                    ArgsString('(int *x, int *y)').annt(0, 'out'))
        c.addMethod('int', 'call_get_coords_ref',
                    ArgsString('(int &x, int &y)').annt(0, 'out'))
        c.addMethod('void', 'call_get_mappedtype_ptr',
                    ArgsString('(string *x, string **y)').annt(0, 'out'))
        c.addMethod('void', 'call_get_mappedtype_ref',
                    ArgsString('(string &x, string *&y)').annt(0, 'out'))
        c.addMethod('void', 'call_get_wrappedtype_ptr',
                    ArgsString('(CtorsClass *x, CtorsClass **y)').annt(0, 'out'))
        c.addMethod('void', 'call_get_wrappedtype_ref',
                    ArgsString('(CtorsClass &x, CtorsClass *&y)').annt(0, 'out'))
        module.addItem(c)

        c = ClassDef(name='MappedTypeClass')
        c.addMethod('string', 'get_name', '()', isVirtual=True)
        c.addMethod('string', 'call_get_name', '()')
        c.addMethod('string', 'concat',
                    ArgsString('(string *s, int len)')
                    .annt(0, 'array').annt(1, 'arraySize'), isVirtual=True)
        c.addMethod('string', 'call_concat',
                    ArgsString('(string *s, int len)')
                    .annt(0, 'array').annt(1, 'arraySize'))
        c.addItem(MemberVarDef(
            type='string', name='m_name'))
        module.addItem(c)

        c = ClassDef(name='WrappedTypeClass')
        c.addMethod('CtorsClass&', 'get_ref', '()', isVirtual=True)
        c.addMethod('CtorsClass&', 'call_get_ref', '()')
        c.addMethod('CtorsClass*', 'get_ptr', '()', isVirtual=True)
        c.addMethod('CtorsClass*', 'call_get_ptr', '()')
        c.addMethod('CtorsClass', 'get_value', '()', isVirtual=True)
        c.addMethod('CtorsClass', 'call_get_value', '()')
        module.addItem(c)

        f = FunctionDef(
            type='void', argsString='(char *name, char *str)',
            name='raise_exception', items=[
                ParamDef(type='char *', name='name'),
                ParamDef(type='char *', name='str')])
        f.setCppCode('WL_SET_EXCEPTION(name, str);')
        module.addItem(f)

        c = ClassDef(name='DetectableBase')
        c.detectSubclassCode_cffi = ("""\
            const char *name = cpp_obj->get_class_name();
            char *ret = (char*)malloc(strlen(name) * sizeof(char));
            strcpy(ret, name);
            return ret;
        """)
        module.addItem(c)
        module.addItem(ClassDef(name='DetectableSubclass',
                                bases=['DetectableBase']))

        module.addItem(FunctionDef(
            type='DetectableBase *', argsString='(bool base)',
            name='get_detectable_object', items=[
                ParamDef(type='bool', name='base')]))

        c = ClassDef(name='VoidPtrClass')
        c.addMethod('void*', 'copy_data', '(void *data, int size)',
                    isVirtual=True)
        c.addMethod('void*', 'call_copy_data', '(void *data, int size)')
        module.addItem(c)

        c = ClassDef(name='DocstringClass', briefDoc='Doc')
        c.addMethod('void', 'docstring_meth', '()', briefDoc='Doc')
        c.addMethod('void', 'docstring_overloaded_meth', '()', briefDoc='Doc')
        c.addMethod('void', 'docstring_overloaded_meth', '(int i)',
                    briefDoc='Doc')
        c.addPyMethod('docstring_pymeth', '(self)', 'pass', 'PyDoc')
        module.addItem(c)

        c = ClassDef(name='TypedefClass')
        c.addMethod('CtorsAlias&', 'passthrough', '(CtorsAlias &obj)')
        module.addItem(c)

        module.cdefs_cffi.append("typedef int(*intcallback)(int);")
        module.headerCode.append("typedef int(*intcallback)(int);")

        c = ClassDef(name='CustomCppMethodsClass')
        c.addItem(CppMethodDef_cffi(
            'CustomCppMethodsClass', isCtor=True,
            pyArgs=ArgsString("(WL_Self self, int i)"),
            pyBody="""\
            ptr = call(i)
            wrapper_lib.init_wrapper(self, ptr, wrapper_lib.hassubclass(self))
            """,

            cReturnType='void*', cArgsString='(int i)',
            cBody="return new WL_CLASS_NAME(i);",
            originalCppArgs=ArgsString('(int i)'))
        )
        c.addMethod('int', 'get', '')
        c.addItem(CppMethodDef_cffi(
            'custom_pycode_only',
            pyArgs=ArgsString("(WL_Self self, int i)"),
            pyBody="""\
            data = ffi.new('int[]', [int(i), 10])
            call(ffi.NULL, data)
            return data[0]
            """,
            cReturnType='void', cArgsString='(void *self, int *data)',
            cBody="static_cast<CustomCppMethodsClass*>(self)->custom_pycode_only(data);"))
        c.addItem(CppMethodDef_cffi(
            'custom_pycode_and_cppcode', isVirtual=True,
            pyArgs=ArgsString("WL_Self self, WL_Object callback"),
            pyBody="""\
            assert callable(callback)
            cb = ffi.callback('int(*)(int)', callback)
            return call(cb)
            """,
            cReturnType='int', cArgsString='(int(*cb)(int))',

            cBody="return cb(10);",

            originalCppType='int',
            originalCppArgs=ArgsString('(intcallback cb)'),

            virtualCReturnType='int',
            virtualCArgsString='(void *self, int(*)(int))',
            virtualCBody="""\
            return call(this, cb);
            """,

            virtualPyArgs="(self, func_ptr)",
            virtualPyBody="""\
            return wrapper_lib.obj_from_ptr(self).custom_pycode_and_cppcode(func_ptr)
            """,
        ))
        c.addItem(CppMethodDef_cffi(
            'call_custom_pycode_and_cppcode',
            pyArgs=ArgsString("WL_Self self, WL_Object callback"),
            pyBody="""\
            assert callable(callback)
            cb = ffi.callback('int(*)(int)', callback)
            return call(wrapper_lib.get_ptr(self), cb)
            """,
            cReturnType='int', cArgsString='(void *self, intcallback cb)',
            cBody="return static_cast<CustomCppMethodsClass*>(self)->call_custom_pycode_and_cppcode(cb);"""
        ))
        c.addItem(CppMethodDef_cffi(
            'overloaded',
            pyArgs=ArgsString('(WL_Self self, int i)'),
            pyBody="return (self, i)"
        ))
        c.addItem(CppMethodDef_cffi(
            'overloaded',
            pyArgs=ArgsString('(WL_Self self)'),
            pyBody="return self"
        ))
        module.addItem(c)

        c = ClassDef(name='MultipleInheritBaseA')
        c.addMethod('', 'MultipleInheritBaseA', '(int a)', isCtor=True)
        c.addItem(MemberVarDef(type='int', name='a'))
        module.addItem(c)

        c = ClassDef(name='MultipleInheritBaseB')
        c.addMethod('', 'MultipleInheritBaseB', '(int b)', isCtor=True)
        c.addItem(MemberVarDef(type='int', name='b'))
        module.addItem(c)

        c = ClassDef(name='MultipleInheritClass',
                     bases=['MultipleInheritBaseA', 'MultipleInheritBaseB'])
        c.addMethod('', 'MultipleInheritBaseA', '(int a, int b, int c)',
                    isCtor=True)
        c.addItem(MemberVarDef(type='int', name='c'))
        module.addItem(c)

        module.addItem(FunctionDef(
            type='OpaqueType*', name='make_opaque_object', argsString='(int i)',
            items=[ParamDef(type='int', name='i')]))
        module.addItem(FunctionDef(
            type='int', name='take_opaque_object', argsString='(OpaqueType *obj)',
            items=[ParamDef(type='OpaqueType *', name='obj')]))

        module.addItem(TypedefDef(type='long long', name='time_t',
                                  platformDependent=True))
        module.addItem(FunctionDef(
            type='void', name='give_me_the_time', argsString='(time_t t)',
            items=[ParamDef(type='time_t', name='t')]))

        module.addPyCode('global_pyclass_int = global_pyclass_inst.i')
        module.addPyCode('global_pyclass_inst = PyClass(9)', order=20)

        module.addPyClass('PyClass', [], 'PyClass docstring', order=10, items=[
            PyCodeDef('SOME_INT = 9'),
            PyFunctionDef('__init__', '(self, i)', 'self._i = i'),
            PyFunctionDef('geti', '(self)', 'return self._i'),
            PyFunctionDef('seti', '(self, i)', 'self._i = i'),
            PyFunctionDef('docstring_pymeth', '(self)', 'pass',
                           briefDoc='PyDoc'),
            PyPropertyDef(name='i', getter='geti', setter='seti')])

        CffiWrapperGenerator.stripIgnoredItems(module.items)
        CffiWrapperGenerator.trimPrefixes(module.items)

        mod_path = cls.tmpdir.join('%s.def' % module.name)
        with mod_path.open('w') as f:
            pickle.dump(module, f)

        gen.generate(module.name)

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

        CffiWrapperGenerator.stripIgnoredItems(module.items)
        CffiWrapperGenerator.trimPrefixes(module.items)

        mod_path = cls.tmpdir.join('%s.def' % module.name)
        with mod_path.open('w') as f:
            pickle.dump(module, f)

        gen.generate(module.name)
        return gen

    @classmethod
    def build_module(cls, name):
        cpp_path = cls.tmpdir.join(name + '.cpp')
        h_path = cls.tmpdir.join(name + '.h')
        py_path = cls.tmpdir.join(name + '.py')
        user_py_path = cls.tmpdir.join(name.strip('_') + '.py')

        test_dir = os.path.dirname(__file__)

        verify_args = {}
        verify_args['include_dirs'] = [test_dir, INCLUDES_DIR]
        verify_args['tmpdir'] = str(cls.tmpdir)
        verify_args['sources'] = [str(cpp_path),
                                  os.path.join(test_dir, 'test_bindgen.cpp')
                                 ]

        link_args = []
        verify_args['extra_link_args'] = link_args
        verify_args['extra_compile_args'] = ["-O0", '-g']

        with cpp_path.open('w') as cpp_file, py_path.open('w') as py_file,\
             user_py_path.open('w') as user_py_file, h_path.open('w') as h_file:
            # Use distutis via cffi to build the cpp code
            cls.gen.write_files(
                name, py_file, user_py_file, cpp_file, h_file, verify_args)

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

    def test_method_with_default(self):
        obj = self.mod.DefaultsClass()
        assert obj.defaults_enum() == self.mod.DefaultsClass.Defaults_A
        assert obj.defaults_array() == -1

        assert obj.defaults_meth() == 15
        assert obj.defaults_meth('test') == 14
        assert obj.defaults_meth('test', 9) == 19
        assert obj.defaults_meth('test', 9, self.mod.CtorsClass(10)) == 23
        assert obj.defaults_meth(i=9) == 20
        assert obj.defaults_meth(c=self.mod.CtorsClass(10)) == 19

    def test_custom_code_func(self):
        assert self.mod.custom_code_global_func() == 1
        assert self.mod.custom_code_global_func_wrappertypes(
                self.mod.CtorsClass(10), 15) == 25

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

    def test_inheritted_virtual_methods(self):
        someobj = self.mod.VMethSubclass()
        class VMethSubclassSubclass(self.mod.VMethSubclass):
            def overridden_vmeth1(self):
                return 9

            def overridden_vmeth2(self):
                return someobj

            def overridden_vmeth3(self, i):
                return 3 * i

            def unoverridden_cppvmeth(self, c):
                return c.swapcase()

        obj = self.mod.VMethClass()
        assert obj.overridden_vmeth1() == 12
        assert obj.call_overridden_vmeth1() == 12
        assert obj.overridden_vmeth2() is None
        assert obj.call_overridden_vmeth2() is None
        assert obj.overridden_vmeth3(6) == 3
        assert obj.call_overridden_vmeth3(6) == 3
        assert obj.unoverridden_cppvmeth('a') == 'z'
        assert obj.call_unoverridden_cppvmeth('a') == 'z'

        obj = self.mod.VMethSubclass()
        assert obj.overridden_vmeth1() == 15
        assert obj.call_overridden_vmeth1() == 15
        assert obj.overridden_vmeth2() is obj
        assert obj.call_overridden_vmeth2() is obj
        assert obj.overridden_vmeth3(6) == 12
        assert obj.call_overridden_vmeth3(6) == 12
        assert obj.unoverridden_cppvmeth('a') == 'z'
        assert obj.call_unoverridden_cppvmeth('a') == 'z'

        obj = VMethSubclassSubclass()
        assert obj.call_overridden_vmeth1() == 9
        assert obj.call_overridden_vmeth2() is someobj
        assert obj.call_overridden_vmeth3(6) == 18
        assert obj.call_unoverridden_cppvmeth('a') == 'A'

    def test_overloaded_virtual_method_inherting(self):
        o = self.mod.OverloadedVMethSubclass()
        assert o.overloaded_vmeth() == 10
        assert o.overloaded_vmeth(8) == 7

        class OverloadedVMethSubSubclass(self.mod.OverloadedVMethSubclass):
            def overloaded_vmeth(self, x=20):
                return x * 2

        o = OverloadedVMethSubSubclass()
        assert o.call_overloaded_vmeth() == 40
        assert o.call_overloaded_vmeth(10) == 20

    def test_pure_virtual_method_private_overriding(self):
        with pytest.raises(TypeError):
            self.mod.PrivateVMethBase()

        o = self.mod.PrivateVMethClass1()
        assert o.call_pvmeth() == 15
        with pytest.raises(NotImplementedError):
            o.pvmeth()

        o = self.mod.PrivateVMethClass2()
        assert o.pvmeth(20) == 10

        assert o.call_pvmeth() == 16
        with pytest.raises(NotImplementedError):
            o.pvmeth()

    def test_subclass_virtual_method_direct_call(self):
        c = self.mod.VMethSubclass()
        assert c.virtual_method(5) == -5
        assert c.call_virtual(5) == -5

    def test_override_subclass_virtual_method(self):
        class VMethSubclassSubclass(self.mod.VMethSubclass):
            def virtual_method(self, i):
                return i * 2

        c = VMethSubclassSubclass()
        assert c.virtual_method(5) == 10
        assert c.call_virtual(5) == 10

    def test_protected_method(self):
        obj = self.mod.PMethClass()
        assert obj.protected_method('a') == 'A'
        assert obj.static_protected_method() == -2

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

        assert obj.static_cppmethod() == 1.0
        assert self.mod.CtorsClass.static_cppmethod() == 1.0

        obj = self.mod.CtorsClass('a')
        assert obj.get() == ord('a')

    def test_overloaded_func(self):
        assert self.mod.overloaded_func() == 20
        assert self.mod.overloaded_func(12) == 6

    def test_virtual_dtor(self):
        obj = self.mod.VDtorClass()
        obj.delete_self()

        # This is a really indirect way of testing that the virtual dtor was
        # called: the object's internal pointer being change to NULL is a side
        # effect of it being deleted.
        assert wrapper_lib.get_ptr(obj) == self.mod.ffi.NULL

    def test_inherited_virtual_dtor(self):
        obj = self.mod.VDtorSubSubclass()
        obj.delete_self()
        assert wrapper_lib.get_ptr(obj) == self.mod.ffi.NULL

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


        from_cref = self.mod.PrivateCCtorReturnWrapperClass.new_by_cref(5)
        assert from_cref.get() == 5
        assert not from_cref._py_owned

        obj = self.mod.PrivateCCtorReturnWrapperClass(5)
        self.mod.wrapper_lib.give_ownership(obj)

        from_cref = obj.self_by_cref()
        assert obj is from_cref

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

        obj = self.mod.ClassWithEnum()
        assert obj.flip(obj.BOOL_FALSE) == obj.BOOL_TRUE

    def test_operators(self):
        obj = self.mod.OperatorsClass(10, 10)
        obj += self.mod.OperatorsClass(2, 1)
        assert obj.x == 12
        assert obj.y == 11

        obj -= self.mod.OperatorsClass(20, 3)
        assert obj.x == -8
        assert obj.y == 8

        obj = -self.mod.OperatorsClass(9, 8)
        assert obj.x == -9
        assert obj.y == -8

    def test_pyint(self):
        obj = self.mod.PyIntClass()
        assert obj.noPyInt('c') == 'c'
        assert obj.onReturn('c') == ord('c')
        assert obj.onParameter(10) == chr(10)
        assert obj.onBoth(10) == 10

        assert obj.overloaded() == ord('c')
        assert obj.overloaded(11) == 11

    def test_char_types(self):
        obj = self.mod.CharTypesClass()
        assert obj.char_scalar(chr(255)) == -1
        assert obj.uchar_scalar(chr(255)) == 255

        assert obj.schar_scalar(chr(1)) == 1
        with pytest.raises(OverflowError):
            obj.schar_scalar(chr(255))

        assert obj.wchar_string('string') == 'string'
        assert obj.typedef_string('string') == 'string'

    def test_nested_typedef(self):
        obj = self.mod.NestedTypedefsClass()
        assert obj.return_typedef(1) == -1

    def test_unsigned_types(self):
        obj = self.mod.UnsignedTypesClass()
        assert obj.u(1) == 2 ** 32 - 1
        assert obj.ui(1) == 2 ** 32 - 1
        assert obj.ull(1) == 2 ** 64 - 1

    def test_array(self):
        AC = self.mod.ArrayClass

        objs = [AC(1), AC(2), AC(3)]
        assert AC.sum(objs) == 6

        objs = [(1, 2), (3, 4)]
        assert AC.sum_mapped_type(objs) == 10

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

    def test_virtual_wrappedtype(self):
        class WrappedTypeSubclass(self.mod.WrappedTypeClass):
            def get_ref(self_):
                return self.mod.CtorsClass(-10)

            def get_ptr(self_):
                return self.mod.CtorsClass(-11)

            def get_value(self_):
                return self.mod.CtorsClass(-12)

        obj = WrappedTypeSubclass()
        assert obj.call_get_ref().get() == -10
        assert obj.call_get_ptr().get() == -11
        assert obj.call_get_value().get() == -12

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
        assert obj.double_refptr(self.mod.CtorsClass(12)).get() == 24
        assert obj.double_ptrptr(self.mod.CtorsClass(13)).get() == 26

        assert obj.double_ptr((1, 2)) == (2, 4)
        assert obj.double_ref((4, 8)) == (8, 16)
        assert obj.double_refptr((8, 7)) == (16, 14)
        assert obj.double_ptrptr((9, 6)) == (18, 12)


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

            def double_refptr(self_, obj):
                import numbers
                if isinstance(obj, numbers.Number):
                    return -obj
                if isinstance(obj, tuple):
                    return (-obj[0], -obj[1])
                if isinstance(obj, self.mod.CtorsClass):
                    obj = self.mod.CtorsClass(-obj.get())
                    return obj

            def double_ptrptr(self_, obj):
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
        assert obj.call_double_refptr(self.mod.CtorsClass(12)).get() == -12
        assert obj.call_double_ptrptr(self.mod.CtorsClass(13)).get() == -13

        assert obj.call_double_ptr((1, 2)) == (-1, -2)
        assert obj.call_double_ref((4, 8)) == (-4, -8)
        assert obj.call_double_refptr((3, 7)) == (-3, -7)
        assert obj.call_double_ptrptr((5, 9)) == (-5, -9)

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
        self.mod.AbstractClass.get_instance()

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

    def test_virtual_parameters_ownership(self):
        obj_from_virtual = [None]
        class Subclass(self.mod.VirtualParametersOwnershipClass):
            def by_value(self, obj):
                obj_from_virtual[0] = obj
            def by_ptr(self, obj):
                obj_from_virtual[0] = obj
            def by_ref(self, obj):
                obj_from_virtual[0] = obj
            def by_cref(self, obj):
                obj_from_virtual[0] = obj
            def by_cref_private_cctor(self, obj):
                obj_from_virtual[0] = obj

        obj = Subclass()

        obj.call_by_value()
        assert obj_from_virtual[0]._py_owned
        obj_from_virtual[0] = None

        obj.call_by_ptr()
        assert not obj_from_virtual[0]._py_owned
        obj_from_virtual[0] = None

        obj.call_by_ref()
        assert not obj_from_virtual[0]._py_owned
        obj_from_virtual[0] = None

        obj.call_by_cref()
        assert obj_from_virtual[0]._py_owned
        obj_from_virtual[0] = None

        obj.call_by_cref_private_cctor()
        assert not obj_from_virtual[0]._py_owned

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

    def test_exceptions_from_cpp(self):
        with pytest.raises(BufferError):
            self.mod.raise_exception('BufferError', '...')

        class MyException(Exception): pass
        wrapper_lib.register_exception(MyException)

        with pytest.raises(MyException):
            self.mod.raise_exception('MyException', '...')

        with pytest.raises(Exception):
            self.mod.raise_exception('NonExistantException', '...')

    def test_autodetect_subclass(self):
        baseobj = self.mod.get_detectable_object(True)
        assert isinstance(baseobj, self.mod.DetectableBase)

        subclassobj = self.mod.get_detectable_object(False)
        assert isinstance(subclassobj, self.mod.DetectableSubclass)

    def test_multiple_inheritance(self):
        o = self.mod.MultipleInheritClass(1, 2, 3)
        assert o.a == 1
        assert o.b == 2
        assert o.c == 3

    def test_cppmethod_cffi(self):
        someint = [-111]
        def set_someint(i):
            # The C code should pass in a 10
            someint[0] = i
            return -15

        obj = self.mod.CustomCppMethodsClass(10)
        assert obj.get() == 10

        assert obj.custom_pycode_only(12) == 22

        # An assert happens inside the generated code for this call
        assert obj.custom_pycode_and_cppcode(set_someint) == -15
        assert someint[0] == 10

        with pytest.raises(TypeError):
            obj.custom_pycode_only("10")

        with pytest.raises(TypeError):
            self.mod.CustomCppMethodsClass()

    def test_override_virtual_cppmethod_cffi(self):
        someint = [-111]
        def set_someint(i):
            someint[0] = i
            return -1

        class CustomCppMethodsSubclass(self.mod.CustomCppMethodsClass):
            def custom_pycode_and_cppcode(self, callback):
                return callback(42)

        obj = CustomCppMethodsSubclass(10)
        assert obj.call_custom_pycode_and_cppcode(set_someint) == -1
        assert someint[0] == 42

    def test_overloaded_cppmethod_cffi(self):
        obj = self.mod.CustomCppMethodsClass(10)
        assert obj.overloaded() is obj
        assert obj.overloaded(10) == (obj, 10)

    def test_voidptr(self):
        class VoidPtrSubclass(self.mod.VoidPtrClass):
            def copy_data(self, data, size):
                return ffi.cast('char*', data) + 1

        ffi = self.mod.ffi

        cdata = ffi.new('char[]', 'test')
        obj = self.mod.VoidPtrClass()

        tmp = obj.copy_data(cdata, len(cdata))
        assert ffi.string(ffi.cast('char*', tmp)) == 'test'

        obj = VoidPtrSubclass()
        tmp = obj.call_copy_data(cdata, len(cdata))
        assert ffi.string(ffi.cast('char*', tmp)) == 'est'

    def test_opaque_type(self):
        obj = self.mod.make_opaque_object(10)
        assert self.mod.take_opaque_object(obj) == 10

    def test_docstrings(self):
        assert self.mod.DocstringClass.__doc__.strip() == 'Doc'
        assert (self.mod.DocstringClass.docstring_meth.__doc__.strip() ==
                'Doc')

        doc = self.mod.DocstringClass.docstring_overloaded_meth.__doc__.strip()
        doc = '\n'.join([i.strip() for i in doc.splitlines()])
        assert (doc == 'Doc\nDoc')

        assert (self.mod.DocstringClass.docstring_pymeth.__doc__.strip() ==
                'PyDoc')

        assert self.mod.PyClass.__doc__.strip() == 'PyClass docstring'
        assert self.mod.PyClass.docstring_pymeth.__doc__.strip() == 'PyDoc'

    def test_typedefs(self):
        obj = self.mod.CtorsAlias(10)

    def test_conversion_failure(self):
        try:
            self.mod.take_broken_mapped_type(object())
        except TypeError as e:
            assert e.message == 'Message'
        else:
            # No exception raised
            assert False
