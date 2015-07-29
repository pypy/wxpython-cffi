from etgtools import CppMethodDef_cffi, ArgsString
import etgtools

def run(module):
    module.addCdef_cffi("""typedef struct { char** data; } wxPyBytesArray;""")
    module.addHeaderCode("""\
    typedef struct { char** data; } wxPyBytesArray;""")

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxPyBytesArray', cType='char**',
        instanceCheck='return isinstance(py_obj, (list, tuple))',
        py2c="""\
        cdata = ffi.cast('char**', clib.malloc(
            ffi.sizeof('char*') * (len(py_obj) + 1)))
        for i in range(len(py_obj)):
            cdata[i] = clib.malloc(len(py_obj[i]) + 1)
            cdata[i][0:len(py_obj[i])] = py_obj[i]
            cdata[i][len(py_obj[i])] = '\\0'
        cdata[len(py_obj)] = ffi.NULL
        return cdata
        """,
        c2cpp="""\
        wxPyBytesArray *ret = new wxPyBytesArray();
        ret->data = cdata;
        return ret;
        """,
        # Not used for input types
        c2py="""return ffi.NULL""",
        cpp2c="""return NULL;""",
    ))
    c = module.find('wxBitmap')
    c.addCppCtor(
        '(wxPyBytesArray* bits)',
        doc="Construct a Bitmap from a list of strings formatted as XPM data.",
        body="""\
        wxBitmap* ret = new wxBitmap(bits->data);
        char** p = bits->data;
        while (*p) free(*p++);
        free(bits->data);
        return ret;
        """)
