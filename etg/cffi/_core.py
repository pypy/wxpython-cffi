from etgtools.extractors import FunctionDef, TypedefDef, GlobalVarDef

def run(module):
    module.addHeaderCode('#include <wx/wx.h>')

    module.addItem(TypedefDef(name='wxCoord', type='int'))

    module.addPyCode('from ._core import *', order=0)

    module.addItem(FunctionDef(
        type='void', argsString='()', name='_wxPyCleanup'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPort', pyName='Port'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPlatform',
                                pyName='Platform'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPlatformInfo',
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
        class PyAssertionError(wxAssertionError):
            pass
        PlatformInfo = tuple(PlatformInfo.strip(', ').split(', '))
        """)
