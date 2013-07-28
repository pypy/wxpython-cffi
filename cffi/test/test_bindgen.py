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
    ModuleDef, ClassDef, MethodDef, FunctionDef, ParamDef)

class TestBindGen(object):
    def setup(self):
        self.tmpdir = pytest.ensuretemp('build', dir=True)
        self.gen = self.create_generator()
        self.mod = self.build_module()

    def create_generator(self):
        module = ModuleDef('bindgen_test', '_core', '_core')
        module.addHeaderCode('#include <test_bindgen.h>')
        module.addItem(FunctionDef(
            type='int', argsString='()', name='simple_global_func',
            pyName='simple_global_func'))
        module.addItem(FunctionDef(
            type='float', argsString='(int i, double j)',
            name='global_func_with_args', pyName='global_func_with_args',
            items=[ParamDef(type='int', name='i'),
                   ParamDef(type='double', name='j')]))
        module.addItem(FunctionDef(
            type='double', argsString='()',
            name='custom_code_func', pyName='custom_code_func',
            cppCode="return custom_code_global_func() - 1;"))

        c = ClassDef(name='SimpleClass')
        c.addItem(MethodDef(
            type='int', argsString='(double f)',
            name='simple_method', pyName='simple_method',
            items=[ParamDef(type='double', name='f')]))

        module.addItem(c)

        mod_path = self.tmpdir.join('%s.def' % module.name)
        with mod_path.open('w') as f:
            pickle.dump(module, f)

        gen = cffi_bindgen.CffiModuleGenerator(module.name,
                                               str(self.tmpdir.join('%s.def')))
        gen.generate({})
        return gen

    def build_module(self):
        cpp_path = self.tmpdir.join('_core.cpp')
        py_path = self.tmpdir.join('_core.py')

        test_dir = os.path.dirname(__file__)
        sources = [str(cpp_path), os.path.join(test_dir, 'test_bindgen.cpp')]
        include_dirs = [test_dir]
        tmpdir = str(self.tmpdir)

        with cpp_path.open('w') as cpp_file, py_path.open('w') as py_file:
            # Use distutis via cffi to build the cpp code
            self.gen.write_files(
                py_file, cpp_file,
                'sources=["%s"], include_dirs=["%s"], tmpdir="%s"' %
                ('", "'.join(sources), '", "'.join(include_dirs), tmpdir))

        return py_path.pyimport()

    def test_simple_global_func(self):
        assert self.mod.simple_global_func() == 10

    def test_global_func_with_args(self):
        assert self.mod.global_func_with_args(10, 2.0) == 20
        assert self.mod.global_func_with_args(12, .25) == 3
        assert self.mod.global_func_with_args(14, .25) == (14 * .25)

    def test_custom_code_func(self):
        assert self.mod.custom_code_func() == 1

    def test_simple_class_init(self):
        self.mod.SimpleClass()

    def test_simple_method(self):
        c = self.mod.SimpleClass()
        assert c.simple_method(5.5) == 5
