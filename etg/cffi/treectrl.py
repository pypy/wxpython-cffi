import etgtools
from etgtools.extractors import ClassDef

def run(module):
    #c = ClassDef(name='wxPyTreeItemData')
    #module.addItem(c)
    module.addHeaderCode('#include <wx/treectrl.h>')
    module.addHeaderCode("""
    typedef WL_RefCountedPyObjBase<wxTreeItemData> wxPyTreeItemData;
    """)
    module.addCppCode("""
    extern "C" void* new_wxPyTreeItemData(void *ptr)
    {
        return new wxPyTreeItemData(ptr);
    }
    """)
    module.addCdef_cffi('void* new_wxPyTreeItemData(void *);')

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxTreeItemData', cType='void*',
        py2c="""\
            with wrapper_lib.get_refcounted_handle(py_obj) as handle:
                return clib.new_wxPyTreeItemData(handle)
        """,
        c2cpp="return (wxPyTreeItemData*)cdata;",
        cpp2c="return ((wxPyTreeItemData*)cpp_obj)->get_handle();",
        c2py="return None if cdata == ffi.NULL else ffi.from_handle(cdata)",
        instanceCheck='return True'))

