import etgtools.tweaker_tools as tools

from etgtools import (
    ModuleDef, DefineDef, MappedTypeDef_cffi, ParamDef, FunctionDef)

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "arrayholder"   # Base name of the file to generate to for this script
DOCSTRING = ""

def run():
    # TODO: Are the mapped types defined in src/arrayholder.sip needed for this
    #       backend? They don't actually work for the sip backend right now...
    module = ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    tools.runGenerators(module)

if __name__ == '__main__':
    run()
