import etgtools

def run(module):
    c = module.find('wxPyApp')

    # Add a new C++ wxPyApp class that adds empty Mac* methods for other
    # platforms, and other goodies, then change the name so SIP will
    # generate code wrapping this class as if it was the wxApp class seen in
    # the DoxyXML.
    c.addHeaderCode('#include "cffi/app_ex.h"')
    c.includeCppCode('src/cffi/app_ex.cpp')

    # Replace the default wrapper that is generated for _BootstrapApp with one
    # that will pass in sys.argv
    c.find('_BootstrapApp').ignore()
    c.addItem(etgtools.CppMethodDef_cffi(
        '_BootstrapApp',
        pyArgs=etgtools.ArgsString('(WL_Self self)'),
        pyBody="""\
        # wxEntryStart (which is called by _BootstrapApp) expects to take
        # ownership of the array passed to it, so allocate with malloc instead
        # of ffi.new.
        argv = clib.malloc(ffi.sizeof('wchar_t*') * (len(sys.argv) + 1))
        argv = ffi.cast('wchar_t**', argv)
        argv[len(sys.argv)] = ffi.NULL

        for i in range(len(sys.argv)):
            arg = clib.malloc(ffi.sizeof('wchar_t') * (len(sys.argv[i]) + 1))
            arg = ffi.cast('wchar_t*', arg)
            argv[i] = arg

            for k, c in enumerate(sys.argv[i]):
                arg[k] = unicode(c)
            arg[len(sys.argv[i])] = u'\\0'

        call(wrapper_lib.get_ptr(self), len(sys.argv), argv)
        wrapper_lib.check_exception(clib)
        """,
        cReturnType='void',
        cArgsString='(void *self, int argc, wchar_t **argv)',
        cBody="static_cast<wxPyApp*>(self)->_BootstrapApp(argc, argv);",
        ))
