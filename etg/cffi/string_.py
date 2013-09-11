import etgtools.tweaker_tools as tools

from etgtools import ModuleDef, DefineDef, MappedTypeDef_cffi

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "string_"   # Base name of the file to generate to for this script
DOCSTRING = ""

def run():
    module = ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addItem(DefineDef(name='wxUSE_UNICODE', value=''))

    module.addItem(MappedTypeDef_cffi(
        name='wxChar', cType='void *',
        py2c="""\
        if wxUSE_UNICODE:
            type_name = 'wchar_t[]'
        else:
            type_name = 'char[]'
        copy = ffi.new(type_name, py_obj)
        return copy
        """,
        c2py="""
        if wxUSE_UNICODE:
            type_name = 'wchar_t*'
        else:
            type_name = 'char*'
        ret = ffi.string(ffi.cast(type_name, cdata))
        return ret
        """,
        c2cpp="return (wxChar*)cdata;",
        cpp2c="return cpp_obj;",
        instancecheck='return isinstance(obj, (str, unicode))',))

    module.addItem(MappedTypeDef_cffi(
        name='wxString', cType='char *',
        py2c="return (ffi.new('char[]', py_obj), None)",
        c2py="""
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        c2cpp="return new wxString(cdata);",
        cpp2c="return wxStrdup(cpp_obj->c_str());",
        instancecheck='return isinstance(obj, (str, unicode))',))

    tools.runGenerators(module)

if __name__ == '__main__':
    run()
