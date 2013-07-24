import os
import sys
import imp
import pickle
import pytest

# Manually add the top-level directory to our path so we can import etgtools
# modules
sys.path.append("../..")
from etgtools import extractors, cffi_bindgen

class TestBindGen(object):
    def setup(self):
        self.tmpdir = pytest.ensuretemp('build', dir=True)
        self.gen = self.create_generator()
        self.mod = self.build_module()

    def create_generator(self):
        module = extractors.ModuleDef('bindgen_test', '_core', '_core')
        module.addHeaderCode('#include <test_bindgen.h>')
        module.addItem(extractors.FunctionDef(
            type='int', argsString='()', name='simple_global_func', items=[]))

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
