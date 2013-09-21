import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "clntdata"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addCppCode("""
    typedef cffiRefCountedPyObjBase<wxClientData> wxPyClientData;

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
                return (clib.new_wxPyClientData(handle), None)
        """,
        c2cpp="return (wxPyClientData*)cdata;",
        cpp2c="return ((wxPyClientData*)cpp_obj)->get_handle();",
        c2py="return None if cdata == ffi.NULL else ffi.from_handle(cdata)",
        instancecheck='return True'))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    

    
#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
