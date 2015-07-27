import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "filename"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    module.addHeaderCode('#include <wx/filename.h>')

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxFileName', cType='const wchar_t *',
        includes=['wx/filename.h'],
        py2c="""\
        cdata = clib.malloc(ffi.sizeof('wchar_t') * (len(py_obj) + 1))
        cdata = ffi.cast('wchar_t*', cdata)
        cdata[0:len(py_obj)] = unicode(py_obj)
        cdata[len(py_obj)] = u'\\0'

        return cdata
        """,
        c2cpp="""\
        wxFileName *ret = new wxFileName(wxString(cdata));
        free((void*)cdata);
        return ret;
        """,

        c2py="""\
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        cpp2c="return wxStrdup(cpp_obj->GetFullPath().wc_str());",
        instanceCheck='return isinstance(py_obj, (str, unicode))',))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
