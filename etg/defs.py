#---------------------------------------------------------------------------
# Name:        etg/defs.py
# Author:      Robin Dunn
#
# Created:     19-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import platform
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "defs"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'defs_8h.xml' ]    
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING,
                                check4unittest=False)
    etgtools.parseDoxyXML(module, ITEMS)
    module.check4unittest = False
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
        
    # tweaks for defs.h
    module.find('wxInt16').type = 'short'
    module.find('wxInt64').type = 'long long'
    module.find('wxUint64').type = 'unsigned long long'
    module.find('wxIntPtr').type =  'long long'           #'ssize_t'
    module.find('wxUIntPtr').type = 'unsigned long long'  #'size_t'
    module.find('wxInt8').pyInt = True
    module.find('wxUint8').pyInt = True
    module.find('wxByte').pyInt = True
    
    module.find('wxDELETE').ignore()
    module.find('wxDELETEA').ignore()
    module.find('wxSwap').ignore()
    module.find('wxVaCopy').ignore()
    
    # Add some typedefs for basic wx types and others so the backend
    # generator knows what they are
    td = module.find('wxUIntPtr')
    module.insertItemAfter(td, etgtools.TypedefDef(type='wchar_t', name='wxUChar'))
    module.insertItemAfter(td, etgtools.TypedefDef(type='wchar_t', name='wxChar'))
    module.insertItemAfter(td, etgtools.TypedefDef(type='long long', name='time_t',
                                                   platformDependent=True))
    module.insertItemAfter(td, etgtools.TypedefDef(type='long long', name='wxFileOffset'))
    module.insertItemAfter(td, etgtools.TypedefDef(type='unsigned char', name='byte', pyInt=True))
    

    
    # Forward declarations for classes that are referenced but not defined
    # yet. 
    # 
    # TODO: Remove these when the classes are added for real.
    # TODO: Add these classes for real :-)
    module.insertItem(0, etgtools.WigCode("""\
        // forward declarations
        class wxPalette;
        class wxExecuteEnv;
        """))
    
   
    # Add some code for getting the version numbers
    module.addCppCode("""
        #include <wx/version.h>
        const int MAJOR_VERSION = wxMAJOR_VERSION;
        const int MINOR_VERSION = wxMINOR_VERSION;           
        const int RELEASE_NUMBER = wxRELEASE_NUMBER;     
        """)
    module.addItem(etgtools.GlobalVarDef(type='const int', name='MAJOR_VERSION'))
    module.addItem(etgtools.GlobalVarDef(type='const int', name='MINOR_VERSION'))
    module.addItem(etgtools.GlobalVarDef(type='const int', name='RELEASE_NUMBER'))

    module.addPyCode("BG_STYLE_CUSTOM = BG_STYLE_PAINT")
    module.addItem(etgtools.DefineDef(name='wxADJUST_MINSIZE', value='0'))
    

    tools.runGeneratorSpecificScript(module)

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

