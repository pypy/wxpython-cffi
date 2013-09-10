from etgtools.extractors import FunctionDef, GlobalVarDef

OTHERDEPS = [ 'src/cffi/core_ex.cpp' ]

def run(module):
    module.addItem(FunctionDef(
        type='void', argsString='()', name='_wxPyCleanup'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPort', pyName='Port'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPlatform',
                                pyName='Platform'))
    module.addItem(GlobalVarDef(type='const char *', name='wxPlatformInfo',
                                pyName='Platform'))

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
        PlatformInfo = tuple(wx._core.PlatformInfo.strip(', ').split(', '))
        """)
