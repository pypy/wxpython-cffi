import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "wxpybuffer"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addCdef_cffi("""\
    typedef struct wxPyBuffer
    {
        size_t m_len;
        char *m_ptr;
    } wxPyBuffer;
    """)
    module.addHeaderCode(tools.textfile_open('src/cffi/wxpybuffer.h').read())

    # We only need this for checking parameters
    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxPyBuffer', cType='wxPyBuffer *',
        py2c="""\
        memview = memoryview(py_obj)
        chardata = ffi.new('char[]', len(memview))
        for i in range(len(memview)):
            chardata[i] = memview[i]

        cdata = ffi.new('wxPyBuffer *')
        cdata.m_len = len(memview)
        cdata.m_ptr = chardata
        return (cdata, (cdata, chardata))
        """,
        c2py="""
        ba = bytearray(ffi.buffer(cdata.m_ptr, cdata.m_len))
        ret = memoryview(ba)
        clib.free(cdata.m_ptr)
        clib.free(cdata)
        return ret
        """,
        c2cpp="return new wxPyBuffer(*cdata);",
        cpp2c="return cpp_obj;",
        instancecheck="""\
        try:
            memoryview(py_obj)
            return True
        except TypeError:
            return False
        """))

    # TODO: Uncomment these when re-adding _stc or stream
    '''
    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxMemoryBuffer', cType='wxPyBuffer *',

        py2c="""
        memview = memoryview(py_obj)
        chardata = ffi.new('char[]', memview.itemsize)
        for i in range(memview.itemsize):
            chardata[i] = memview[i]

        cdata = ffi.new('wxPyBuffer *')
        cdata.len = memview.itemsize
        cdata.data = chardata
        return (cdata, (cdata, chardata))
        """,

        c2cpp="return new wxCharBuffer(cdata);",

        cpp2c="""\
        char *cdata = (char*)malloc(cpp_obj->length() + 1);
        memcpy(cdata, (char*)cpp_obj->GetData(), cpp_obj->GetDataLen());
        return cdata;
        """,
        c2py="""
        ret = bytearr
        clib.free(cdata)
        return ret
        """,
        instancecheck="""
        try:
            memoryview(py_obj)
            return True
        except TypeError:
            return False
        """))

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxCharBuffer', cType='char*',

        py2c="return (ffi.new('char[]', py_obj), None)",
        c2cpp="return new wxCharBuffer(cdata);",

        cpp2c="""\
        char *cdata = (char*)malloc(cpp_obj->length() + 1);
        strcpy(cdata, cpp_obj->data());
        return cdata;
        """,
        c2py="""
        ret = ffi.string(cdata)
        clib.free(cdata)
        return ret
        """,
        instancecheck="return isinstance(py_obj, str)"))
    '''

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
