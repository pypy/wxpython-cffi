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
int cffifunc_string_len_cb();
void * (*get_string_fake_virtual_ptr)();
void * cffimtype_string_c2cpp(char *);
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
        return (ffi.new('char[]', obj), None)

    @staticmethod
    def c2py(obj):
        string = ffi.string(obj)
        clib.free(obj)
        return string

StringMappedTypeSeq = wrapper_lib.create_array_type(
    StringMappedType, ctype="char *")

def string_len(s):
    assert isinstance(s, StringMappedType)
    s, s_keepalive = StringMappedType.py2c(s)
    return clib.cffifunc_string_len(s)

def total_string_len(s):
    assert isinstance(s, StringMappedTypeSeq)
    s, _array_length_, s_keepalive = StringMappedTypeSeq.py2c(s)
    return clib.cffifunc_total_string_len(s, _array_length_)

global_string = StringMappedType.c2py(clib.cffigvar_global_string)

def get_string():
    return "get_string"

@ffi.callback('void*(*)()')
def get_string_fake_virtual_wrapper():
    pyresult = get_string()
    cdata, keepaliave = StringMappedType.py2c(pyresult)
    return clib.cffimtype_string_c2cpp(cdata)

clib.get_string_fake_virtual_ptr = get_string_fake_virtual_wrapper

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

    def test_fake_virtual(self):
        assert clib.cffifunc_string_len_cb() == 10
