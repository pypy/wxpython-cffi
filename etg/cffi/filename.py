import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "filename"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxFileName', cType='const wchar_t *',
        py2c="return (ffi.new('wchar_t[]', py_obj), None)",
        c2py="""
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        c2cpp="return new wxFileName(wxString(cdata));",
        cpp2c="return wxStrdup(cpp_obj->GetFullPath().wc_str());",
        instancecheck='return isinstance(py_obj, (str, unicode))',))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
