from etgtools.extractors import FunctionDef, TypedefDef, GlobalVarDef

def run(module):
    module.addHeaderCode('#include <wx/wx.h>')

    module.addItem(TypedefDef(name='wxCoord', type='int'))

    module.addPyCode('''\
    from ._core import *
    from . import _core
    ''', order=0)

    module.addItem(FunctionDef(
        type='void', argsString='()', name='_wxPyCleanup'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPyPort',
                                pyName='Port'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPyPlatform',
                                pyName='Platform'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPyPlatformInfo',
                                pyName='PlatformInfo'))

    module.includeCppCode('src/cffi/core_ex.cpp')

    module.addInitializerCode("""\
        wxPyPreInit();
        """)
    module.addPostInitializerCode("""\
        wxPyCoreModuleInject();
        """)

    module.addPyCode("""\
        class wxAssertionError(Exception):
            pass
        wrapper_lib.register_exception(wxAssertionError)
        class PyAssertionError(wxAssertionError):
            pass
        wrapper_lib.register_exception(PyAssertionError)
        PlatformInfo = tuple(PlatformInfo.strip(', ').split(', '))
        """)
