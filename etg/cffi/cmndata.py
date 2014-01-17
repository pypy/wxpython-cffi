from etgtools import CppMethodDef_cffi, ArgsString

def run(module):
    c = module.find('wxPrintData')

    c.addItem(CppMethodDef_cffi(
        'GetPrivData', ArgsString('(WL_Self self)'),
        """\
        size = ffi.new('int*')
        charp = call(wrapper_lib.get_ptr(self, PrintData), size)

        # ffi.string won't read past a null, which must be allowed here
        return ''.join(charp[0:size[0]])
        """,

        'char*', '(void *self_, int *len)',
        """\
        wxPrintData *self = (wxPrintData *)self_;
        *len = self->GetPrivDataLen();
        return self->GetPrivData();
        """))

    c.addItem(CppMethodDef_cffi(
        'SetPrivData', ArgsString('(WL_Self self, WL_Object data)'),
        """\
        if not isinstance(data, str):
            raise TypeError("Expected string object")

        call(wrapper_lib.get_ptr(self, PrintData), data, len(data))
        """,

        'void', '(void *self_, char *data, int len)',
        """\
        wxPrintData *self = (wxPrintData *)self_;
        self->SetPrivData(data, len);
        """))

    c.addProperty('PrivData GetPrivData SetPrivData')
