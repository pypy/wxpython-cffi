import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "clntdata"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addHeaderCode("""
    typedef WL_RefCountedPyObjBase<wxClientData> wxPyClientData;
    """)

    module.addCppCode("""
    extern "C" void* new_wxPyClientData(void *ptr)
    {
        return new wxPyClientData(ptr);
    }
    """)
    module.addCdef_cffi('void* new_wxPyClientData(void *);')

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxClientData', cType='void*',
        py2c="""\
            with wrapper_lib.get_refcounted_handle(py_obj) as handle:
                return clib.new_wxPyClientData(handle)
        """,
        c2cpp="return (wxPyClientData*)cdata;",
        cpp2c="return cpp_obj?((wxPyClientData*)cpp_obj)->get_handle():NULL;",
        c2py="return None if cdata == ffi.NULL else ffi.from_handle(cdata)",
        instanceCheck='return True'))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    

    
#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
