import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "arrays"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxArrayString', cType='wchar_t **',
        py2c="""\
        # The array's last item will be NULL pointer to mark the end
        cdata = ffi.new('wchar_t *[]', len(py_obj) + 1)

        keepalive = [cdata]
        for i, obj in enumerate(py_obj):
            charp = ffi.new('wchar_t[]', obj)
            keepalive.append(charp)
            cdata[i] = charp

        return (cdata, keepalive)
        """,
        c2cpp="""\
        int i;
        for(i = 0; cdata[i] != NULL; i++) ;
        return new wxArrayString(i, (const wchar_t**)cdata);
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


        instancecheck="""\
        if (not isinstance(py_obj, collections.Sequence) or
            isinstance(py_obj, (str, unicode))):
            return False
        return all(isinstance(i, (str, unicode)) for i in py_obj)
        """
    ))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
