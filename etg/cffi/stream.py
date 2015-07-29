import etgtools
import etgtools.tweaker_tools as tools

from etgtools.extractors import ClassDef, CppMethodDef_cffi, ParamDef

def run(module):
    # Include a C++ class that can wrap a Python file-like object so it can
    # be used as a wxInputStream
    c = ClassDef(name='wxPyInputStream')
    c.includeCppCode('src/cffi/stream_input.cpp')
    module.addItem(c)
    c.addItem(CppMethodDef_cffi(
        c.name, isCtor=True,
        pyArgs=etgtools.ArgsString('(WL_Self self, WL_Object file)'),
        pyBody="""\
        with wrapper_lib.get_refcounted_handle(file) as handle:
            self._cpp_obj = call(handle)
        """,
        cReturnType='void*',
        cArgsString='(void *handle)',
        cBody="return new WL_CLASS_NAME(handle);",
        originalCppArgs=etgtools.ArgsString('(void *handle)'),
    ))

    # Add the following code to the class body to initialize the callback
    module.addCdef_cffi("""\
    size_t (*PyInputStream_OnSysRead)(void*, void*, size_t);
    int (*PyInputStream_IsSeekable)(void*);
    size_t (*PyInputStream_TellI)(void*);
    size_t (*PyInputStream_SeekI)(void*, size_t, int);
    """)
    c.pyCode_cffi = """\
    @ffi.callback('size_t(*)(void*, void*, size_t)')
    def _PyInputStream_OnSysRead(handle, buffer, bufsize):
        file = ffi.from_handle(handle)
        data = file.read(bufsize)
        ffi.cast('char*', buffer)[0:len(data)] = data
        return len(data)
    clib.PyInputStream_OnSysRead = _PyInputStream_OnSysRead
 
    @ffi.callback('int(*)(void*)')
    def _PyInputStream_IsSeekable(handle):
        file = ffi.from_handle(handle)
        return hasattr(file, 'seek')
    clib.PyInputStream_IsSeekable = _PyInputStream_IsSeekable

    @ffi.callback('size_t(*)(void*)')
    def _PyInputStream_TellI(handle):
        file = ffi.from_handle(handle)
        return file.tell()
    clib.PyInputStream_TellI = _PyInputStream_TellI

    @ffi.callback('size_t(*)(void*, size_t, int)')
    def _PyInputStream_SeekI(handle, pos, whence):
        file = ffi.from_handle(handle)
        file.seek(pos, whence)
        return file.tell()
    clib.PyInputStream_SeekI = _PyInputStream_SeekI
    """

