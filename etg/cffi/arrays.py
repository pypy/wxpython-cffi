import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "arrays"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    struct = """\
    typedef struct wxPyArrayHelper
    {
        size_t length;
        void* array;
    } wxPyArrayHelper;
    """

    module.addHeaderCode(struct)
    module.addCdef_cffi(struct)

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxArrayString', cType='wchar_t **',
        py2c="""\
        array = clib.malloc(ffi.sizeof('wchar_t*') * (len(py_obj) + 1))
        array = ffi.cast('wchar_t **', array)
        # The array's last item will be NULL pointer to mark the end
        array[len(py_obj)] = ffi.NULL

        for i, obj in enumerate(py_obj):
            array_item = clib.malloc(ffi.sizeof('wchar_t*') * len(obj) + 1)
            array_item = ffi.cast('wchar_t*', array_item)
            array[i] = array_item

            array_item[0:len(obj)] = unicode(obj)
            array_item[len(obj)] = u'\0'

        return array
        """,
        c2cpp="""\
        int i;
        for(i = 0; cdata[i] != NULL; i++) ;
        wxArrayString *ret = new wxArrayString(i, (const wchar_t**)cdata);

        for(i = 0; cdata[i] != NULL; i++)
            free(cdata[i]);
        free(cdata);

        return ret;
        """,

        cpp2c="""\
        wchar_t **array = (wchar_t**)malloc(sizeof(wchar_t) * cpp_obj->size() + 1);
        array[cpp_obj->size()] = NULL;

        for(int i = 0; i < cpp_obj->size(); i++)
            array[i] = wxStrdup(cpp_obj->Item(i).wc_str());

        return array;
        """,
        c2py="""\
        cdata_len = 0
        while cdata[cdata_len] != ffi.NULL:
            cdata_len += 1

        ret = []
        for i in range(cdata_len):
            ret.append(ffi.string(cdata[i]))
            clib.free(cdata[i])

        clib.free(cdata)
        return ret
        """,


        instanceCheck="""\
        if (not isinstance(py_obj, collections.Sequence) or
            isinstance(py_obj, (str, unicode))):
            return False
        return all(isinstance(i, (str, unicode)) for i in py_obj)
        """
    ))

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxArrayInt', cType='wxPyArrayHelper*',
        py2c="""\
        array = clib.malloc(ffi.sizeof('int') * len(py_obj))
        array = ffi.cast('int*', array)
        for i, obj in enumerate(py_obj):
            array[i] = int(obj)

        cdata = ffi.new('wxPyArrayHelper*')
        cdata.length = len(py_obj)
        cdata.array = array

        return cdata
        """,
        c2cpp="""\
        int *carray = (int*)cdata->array;

        wxArrayInt *array = new wxArrayInt;
        for(int i = 0; i < cdata->length; i++)
            array->Add(carray[i]);

        free(cdata->array);
        return array;
        """,

        cpp2c="""\
        int *array = (int*)malloc(sizeof(int) * cpp_obj->size());

        for(int i = 0; i < cpp_obj->size(); i++)
            array[i] = cpp_obj->Item(i);

        wxPyArrayHelper* ret = (wxPyArrayHelper*)malloc(sizeof(wxPyArrayHelper));
        ret->array = array;
        ret->length = cpp_obj->size();

        return ret;
        """,
        c2py="""\
        ret = []
        array = ffi.cast('int*', cdata.array)
        for i in range(cdata):
            ret.append(array[i])

        clib.free(cdata.array)
        clib.free(cdata)
        return ret
        """,

        instanceCheck="""\
        if (not isinstance(py_obj, collections.Sequence) or
            isinstance(py_obj, (str, unicode))):
            return False
        return all(isinstance(i, numbers.Number) for i in py_obj)
        """
    ))

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxArrayDouble', cType='wxPyArrayHelper',
        py2c="""\
        array = clib.malloc(ffi.sizeof('double') * len(py_obj))
        array = ffi.cast('double*', array)
        for i, obj in enumerate(py_obj):
            array[i] = float(obj)

        cdata = ffi.new('wxPyArrayHelper*')
        cdata.length = len(py_obj)
        cdata.array = array

        return cdata
        """,
        c2cpp="""\
        double *carray = (double*)cdata.array;

        wxArrayDouble *array = new wxArrayDouble;
        for(int i = 0; i < cdata.length; i++)
            array->Add(carray[i]);
        return array;
        """,

        cpp2c="""\
        double *array = (double*)malloc(sizeof(double) * cpp_obj->size());

        for(int i = 0; i < cpp_obj->size(); i++)
            array[i] = cpp_obj->Item(i);

        wxPyArrayHelper ret;
        ret.array = array;
        ret.length = cpp_obj->size();

        return ret;
        """,
        c2py="""\
        ret = []
        array = ffi.cast('double*', cdata.array)
        for i in range(cdata):
            ret.append(array[i])

        clib.free(cdata.array)
        return ret
        """,

        instanceCheck="""\
        if (not isinstance(py_obj, collections.Sequence) or
            isinstance(py_obj, (str, unicode))):
            return False
        return all(isinstance(i, numbers.Number) for i in py_obj)
        """
    ))
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
