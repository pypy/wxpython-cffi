import etgtools

OTHERDEPS = [ 'src/core_ex.cpp' ]

def run(module):
    module.addHeaderCode('#include <wxpy_api.h>')
    # This code is inserted into the module initialization function
    module.addInitializerCode("""\
        wxPyPreInit(sipModuleDict);
        """)
    module.addPostInitializerCode("""\
        wxPyCoreModuleInject(sipModuleDict);
        """)
    # Here is the function it calls
    module.includeCppCode('src/core_ex.cpp')
    module.addItem(etgtools.WigCode("void _wxPyCleanup();"))
