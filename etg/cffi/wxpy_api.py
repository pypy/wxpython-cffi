import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "wxpy_api"   # Base name of the file to generate to for this script
DOCSTRING = ""

OTHERDEPS = [ 'src/cffi/wxpy_api.h' ]


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    module.addHeaderCode('#include "cffi/wxpy_api.h"')

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    

    
#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
