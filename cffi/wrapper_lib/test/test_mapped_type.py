import cffi
import pytest
import wrapper_lib
from os import path

ffi = cffi.FFI()
cdefs = """
void free(void*);
int cffifunc_string_len(char *);
int cffifunc_total_string_len(char **, int);
extern char * cffigvar_global_string;
"""

ffi.cdef(cdefs)
clib = ffi.verify(
    cdefs,
    sources=[path.join(path.dirname(__file__), 'test_mapped_type.cpp')])

class StringMappedType(wrapper_lib.MappedBase):
    @staticmethod
    def __instancecheck__(obj):
        return isinstance(obj, (str, unicode))

    @staticmethod
    def py2c(obj):
        return ffi.new('char[]', obj)

    @staticmethod
    def c2py(obj):
        string = ffi.string(obj)
        clib.free(obj)
        return string

StringMappedTypeSeq = wrapper_lib.create_mapped_type_seq(
    StringMappedType, "char *", ffi)

def string_len(s):
    assert isinstance(s, StringMappedType)
    return clib.cffifunc_string_len(StringMappedType.py2c(s))

def total_string_len(s):
    assert isinstance(s, StringMappedTypeSeq)
    s, s_keepalive = StringMappedTypeSeq.py2c(s)
    return clib.cffifunc_total_string_len(s, len(s))

global_string = StringMappedType.c2py(clib.cffigvar_global_string)

class TestMappedTypes(object):
    def test_no_subclassing(self):
        with pytest.raises(TypeError):
            class subclass(StringMappedType):
                pass

    def test_param(self):
        assert string_len('string') == 6

    def test_param_seq(self):
        assert total_string_len(['some', 'string']) == 10

    def test_global_variable(self):
        assert global_string == 'global'

    def test_global_array(self):
        assert global_string == 'global'
