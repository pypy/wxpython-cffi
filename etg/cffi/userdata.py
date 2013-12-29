import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "userdata"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addCppCode("""
    typedef WL_RefCountedPyObjBase<wxObject> wxPyUserData;

    extern "C" void* new_wxPyUserData(void *ptr)
    {
        return new wxPyUserData(ptr);
    }
    """)
    module.addCdef_cffi('void* new_wxPyUserData(void *);')

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxPyUserData', cType='void*',
        py2c="""\
            with wrapper_lib.get_refcounted_handle(py_obj) as handle:
                return (clib.new_wxPyUserData(handle), None)
        """,
        c2cpp="return (wxPyUserData*)cdata;",
        cpp2c="return ((wxPyUserData*)cpp_obj)->get_handle();",
        c2py="return None if cdata == ffi.NULL else ffi.from_handle(cdata)",
        instanceCheck='return True'))


    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

