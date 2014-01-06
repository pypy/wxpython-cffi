import etgtools.tweaker_tools as tools

from etgtools import (
    ModuleDef, DefineDef, MappedTypeDef_cffi, ParamDef, FunctionDef)

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "wxstring"   # Base name of the file to generate to for this script
DOCSTRING = ""

def run():
    module = ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addItem(MappedTypeDef_cffi(
        name='wxString', cType='const wchar_t *',
        py2c="""\
        cdata = clib.malloc(ffi.sizeof('wchar_t') * len(py_obj) + 1)
        cdata = ffi.cast('wchar_t*', cdata)
        cdata[0:len(py_obj)] = unicode(py_obj)
        cdata[len(py_obj)] = u'\0'

        return cdata;""",
        c2cpp="""\
        wxString *ret = new wxString(cdata);
        free(cdata);
        return ret;
        """,
        c2py="""\
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        cpp2c="return wxStrdup(cpp_obj->wc_str());",
        instanceCheck='return isinstance(py_obj, (str, unicode))',))

    # Used just for testing the MappedType code, it can be removed later
    module.addItem(FunctionDef(
        type='wxString', name='testStringTypemap',
        argsString='(const wxString& str)',
        items=[ParamDef(type='const wxString&', name='str')]))

    module.addCppCode("""\
    wxString testStringTypemap(const wxString& str)
    {
        wxString local = str;
        return local;
    }
    """)

    tools.runGenerators(module)

if __name__ == '__main__':
    run()
