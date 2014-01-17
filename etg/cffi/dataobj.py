import etgtools
from etgtools import CppMethodDef_cffi, ArgsString

def addGetAllFormats(klass, pureVirtual=False):
    # Replace the GetAllFormats method with an implementation that returns
    # the formats as a Python list
    m = klass.findItem('GetAllFormats')
    if m:
        m.ignore()

    #default = 'Get' if klass.name == 'wxDataObject' else 'DataObject.Get'
    klass.addItem(CppMethodDef_cffi(
        # Python args
        'GetAllFormats',
        ArgsString('(WL_Self self, wxDataObject::Direction dir=wrapper_lib.default_arg_indicator)'),
        """\
        if dir is wrapper_lib.default_arg_indicator:
            dir = DataObject.Get

        size = ffi.new('int*')

        objs = call(wrapper_lib.get_ptr(self), int(dir), size)

        formats = []
        for i in range(size[0]):
            formats.append(wrapper_lib.obj_from_ptr(objs[i], DataFormat, True))

        clib.free(objs)
        return formats
        """,

        # C args
        'void**', '(void *self_, int dir, int *len)',
        """\
        WL_CLASS_NAME *self = (WL_CLASS_NAME*)self_;

        size_t count = self->GetFormatCount((wxDataObject::Direction)dir);
        *len = count;

        wxDataFormat *formats_tmp = new wxDataFormat[count];
        wxDataFormat **formats = (wxDataFormat **)malloc(sizeof(wxDataFormat *) * count);
        self->GetAllFormats(formats_tmp, (wxDataObject::Direction)dir);

        for(int i = 0; i < count; i++)
            formats[i] = new wxDataFormat(formats_tmp[i]);

        delete[] formats_tmp;
        return (void**)formats;
        """,

        # Original C++ args
        'void', ArgsString('(wxDataFormat *formats, wxDataObject::Direction dir)'),

        # Virtual handler C args
        'void**', '(void *, int, int*)',
        """\
        int len;
        wxDataFormat** formats_tmp = (wxDataFormat**)call((void*)this, dir, &len);

        for(int i = 0; i < len; i++)
            formats[i] = *formats_tmp[i];

        free(formats_tmp);
        """,

        # Virtual handler Python args
        "(self, direction, size)",
        """\
        self = wrapper_lib.obj_from_ptr(self, wl_cls)
        formats = self.GetAllFormats(direction)

        cdata = ffi.cast('void**', clib.malloc(ffi.sizeof('void*') * len(formats)))

        for i, format in enumerate(formats):
            cdata[i] = wrapper_lib.get_ptr(format, DataFormat)

        size[0] = len(formats)
        return cdata
        """,

        # Misc
        isVirtual=True,
        isPureVirtual=pureVirtual,
        isConst=True,
        doc="""\
            Returns a list of wx.DataFormat objects which this data object
            supports transfering in the given direction.""",
    ))

def add_GetDataHere_with_format(c, pureVirtual=False):
    # Replace the GetDataHere method with a version that uses a smarter
    # Python buffer object instead of a stupid void pointer.
    c.find('GetDataHere').ignore()
    c.addItem(CppMethodDef_cffi(
        # Python args
        'GetDataHere',
        ArgsString('(WL_Self self, const wxDataFormat& format, wxPyBuffer* buf)'),
        """\
        size = ffi.new('int*')
        res = call(
            wrapper_lib.get_ptr(self, wl_cls),
            wrapper_lib.get_ptr(format, DataFormat),
            size
        )

        if res == ffi.NULL:
            return False

        try:
            size = size[0]
            memoryview(buf)[0:size] = ffi.buffer(res, size)
        except Exception:
            raise
        finally:
            clib.free(res)

        return True
        """,

        # C Args
        'char*', '(void *self_, void *format_, int *size)',
        """\
        {0} *self = ({0}*)self_;
        wxDataFormat *format = (wxDataFormat*)format_;
        void *buf = malloc(self->GetDataSize(*format));

        *size = self->GetDataSize(*format);
        bool res = self->GetDataHere(*format, buf);
        if(res)
            return (char*)buf;
        else
        {{
            free(buf);
            return NULL;
        }}
        """.format(c.name),

        # Original C++ args
        'bool', ArgsString('(const wxDataFormat& format, void* buf)'),

        # Virtual handler C args
        'int', '(void *self, void *format, char *buf)',
        """\
        return (bool)call((void*)this, (void*)&format, (char*)buf);
        """,

        # Virtual handler Python args
        '(self, format, buf)',
        """\
        self = wrapper_lib.obj_from_ptr(self, wl_cls)
        format = wrapper_lib.obj_from_ptr(self, DataFormat)
        size = int(self.GetDataSize(format))
        return int(self.GetDataHere(format, ffi.buffer(buf, size)))
        """,

        # Misc
        isVirtual=True,
        isPureVirtual=pureVirtual,
        isConst=True,
    ))

def add_SetData_with_format(c):
    # Replace the SetData method with an implementation that uses Python
    # buffer objects.
    c.find('SetData').ignore()
    c.addItem(CppMethodDef_cffi(
        # Python args
        'SetData',
        ArgsString('(WL_Self self, const wxDataFormat& format, wxPyBuffer* buf)'),
        """\
        mv = memoryview(buf)

        buf_tmp = ffi.new('char[]', len(mv))
        buf_tmp[0:len(mv)] = mv[:]

        return bool(call(
            wrapper_lib.get_ptr(self, wl_cls),
            wrapper_lib.get_ptr(format, DataFormat),
            len(mv),
            ffi.cast('void*', buf_tmp)
        ))
        """,

        # C args
        'int', "(void *self_, void *format_, int len, void *buf)",
        """\
        WL_CLASS_NAME *self = (WL_CLASS_NAME*)self_;
        wxDataFormat *format = (wxDataFormat*)format_;
        return (int)self->SetData(*format, len, buf);
        """,

        # Original C++ args
        'bool',
        ArgsString('(const wxDataFormat& format, size_t len, const void* buf)'),

        # Virtual handler C args
        'int', '(void *self, void *format, int size, char *buf)',
        """\
        return (bool)call((void*)this, (void*)&format, len, (char*)buf);
        """,

        # Virtual handler Python args
        '(self, format, size, buf)',
        """\
        self = wrapper_lib.obj_from_ptr(self, wl_cls)
        format = wrapper_lib.obj_from_ptr(self, DataFormat)
        return int(self.SetData(format, ffi.buffer(buf, size)))
        """,

        # Misc
        isVirtual=True
    ))

def add_GetDataHere_without_format(c, pureVirtual=False):
    c.find('GetDataHere').ignore()
    c.addItem(CppMethodDef_cffi(
        # Python args
        'GetDataHere',
        ArgsString('(WL_Self self, wxPyBuffer* buf)'),
        """\
        size = ffi.new('int*')
        res = call(
            wrapper_lib.get_ptr(self, wl_cls),
            size
        )

        if res == ffi.NULL:
            return False

        try:
            size = size[0]
            memoryview(buf)[0:size] = ffi.buffer(res, size)
        except Exception:
            raise
        finally:
            clib.free(res)

        return True
        """,

        # C Args
        'char*', '(void *self_, int *size)',
        """\
        {0} *self = ({0}*)self_;
        void *buf = malloc(self->GetDataSize());

        *size = self->GetDataSize();
        bool res = self->GetDataHere(buf);
        if(res)
            return (char*)buf;
        else
        {{
            free(buf);
            return NULL;
        }}
        """.format(c.name),

        # Original C++ args
        'bool', ArgsString('(void* buf)'),

        # Virtual handler C args
        'int', '(void *self, char *buf)',
        """\
        return (bool)call((void*)this, (char*)buf);
        """,

        # Virtual handler Python args
        '(self, buf)',
        """\
        self = wrapper_lib.obj_from_ptr(self, wl_cls)
        size = int(self.GetDataSize())
        return int(self.GetDataHere(buf[0:size]))
        """,

        # Misc
        isVirtual=True,
        isPureVirtual=pureVirtual,
        isConst=True,
    ))

def add_SetData_without_format(c):
    c.find('SetData').ignore()
    c.addItem(CppMethodDef_cffi(
        # Python args
        'SetData',
        ArgsString('(WL_Self self, wxPyBuffer* buf)'),
        """\
        mv = memoryview(buf)

        buf_tmp = ffi.new('char[]', len(mv))
        buf_tmp[0:len(mv)] = mv[:]

        return bool(call(
            wrapper_lib.get_ptr(self, wl_cls),
            len(mv),
            ffi.cast('void*', buf_tmp)
        ))
        """,

        # C args
        'int', "(void *self_, int len, void *buf)",
        """\
        WL_CLASS_NAME *self = (WL_CLASS_NAME*)self_;
        return (int)self->SetData(len, buf);
        """,

        # Original C++ args
        'bool',
        ArgsString('(size_t len, const void* buf)'),

        # Virtual handler C args
        'int', '(void *self, int size, char *buf)',
        """\
        return (bool)call((void*)this, len, (char*)buf);
        """,

        # Virtual handler Python args
        '(self, size, buf)',
        """\
        self = wrapper_lib.obj_from_ptr(self, wl_cls)
        return int(self.SetData(buf[0:size]))
        """,

        # Misc
        isVirtual=True
    ))

def run(module):
    pass
    c = module.find('wxDataObject')

    addGetAllFormats(c, True)
    add_GetDataHere_with_format(c, True)
    add_SetData_with_format(c)

    #------------------------------------------------------------
    c = module.find('wxDataObjectSimple')

    c.addItem(CppMethodDef_cffi(
        'wxDataObjectSimple', ArgsString('WL_Self self, const wxString& formatName)'),
        """\
        ptr = call(wxString.to_c(formatName))
        wrapper_lib.init_wrapper(self, ptr, wrapper_lib.hassubclass(type(self)))
        """,

        'void*', '(const wchar_t *str)',
        """\
        wxString *str_converted = WL_mappedtype<wxString, const wchar_t*>::to_cpp(str);
        WL_CLASS_NAME * ptr = new WL_CLASS_NAME(wxDataFormat(*str_converted));
        delete str_converted;
        return (void*)ptr;
        """,

        isCtor=True))

    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')

    addGetAllFormats(c)
    add_GetDataHere_without_format(c)
    add_SetData_without_format(c)

    #------------------------------------------------------------
    c = module.find('wxCustomDataObject')


    c.addItem(CppMethodDef_cffi(
        'wxCustomDataObject', ArgsString('WL_Self self, const wxString& formatName)'),
        """\
        ptr = call(wxString.to_c(formatName))
        wrapper_lib.init_wrapper(self, ptr, wrapper_lib.hassubclass(type(self)))
        """,

        'void*', '(const wchar_t *str)',
        """\
        wxString *str_converted = WL_mappedtype<wxString, const wchar_t*>::to_cpp(str);
        WL_CLASS_NAME * ptr = new WL_CLASS_NAME(wxDataFormat(*str_converted));
        delete str_converted;
        return (void*)ptr;
        """,

        isCtor=True))

    c.find('GetData').ignore()
    c.addItem(CppMethodDef_cffi(
        'GetData', ArgsString('(WL_Self self)'),
        """\
        data = call(wrapper_lib.get_ptr(self, wl_cls))
        return memoryview(ffi.buffer(data, self.GetSize()))
        """,

        'char*', '(void *self_)',
        """\
        WL_CLASS_NAME *self = (WL_CLASS_NAME*)self_;
        return (char*)self->GetData();
        """,
        isConst=True,
    ))
    add_SetData_without_format(c)

    #------------------------------------------------------------
    c = module.find('wxDataObjectComposite')

    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')

    addGetAllFormats(c)

    #------------------------------------------------------------
    c = module.find('wxTextDataObject')
    addGetAllFormats(c)

    #------------------------------------------------------------
    c = module.find('wxURLDataObject')

    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')

    addGetAllFormats(c)
    add_GetDataHere_without_format(c)
    add_SetData_without_format(c)
