import etgtools.tweaker_tools as tools

from etgtools import ModuleDef, DefineDef, MappedTypeDef_cffi

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "wxstring"   # Base name of the file to generate to for this script
DOCSTRING = ""

def run():
    module = ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addItem(MappedTypeDef_cffi(
        name='wxString', cType='const wchar_t *',
        py2c="return (ffi.new('wchar_t[]', py_obj), None)",
        c2py="""
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        c2cpp="return new wxString(cdata);",
        cpp2c="return wxStrdup(cpp_obj->wc_str());",
        instancecheck='return isinstance(py_obj, (str, unicode))',))

    tools.runGenerators(module)

if __name__ == '__main__':
    run()
