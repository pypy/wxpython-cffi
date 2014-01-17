#---------------------------------------------------------------------------
# Name:        etg/accel.py
# Author:      Kevin Ollivier
#              Robin Dunn
#
# Created:     06-Sept-2011
# Copyright:   (c) 2013 by Wide Open Technologies
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "accel"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxAcceleratorEntry', 'wxAcceleratorTable', ]    
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.

    c = module.find('wxAcceleratorEntry')
    assert isinstance(c, etgtools.ClassDef)
    tools.removeVirtuals(c)

    c = module.find('wxAcceleratorTable')
    assert isinstance(c, etgtools.ClassDef)
    tools.removeVirtuals(c)    
       
    # Mac doesn't have this, and we don't real with resource files from
    # wxPython anyway.
    c.find('wxAcceleratorTable').findOverload('resource').ignore()
    
    # Ignore the current constructor
    # This constructor is replace in generator specific scripts
    c.find('wxAcceleratorTable').findOverload('entries').ignore()
    
    module.addPyFunction('GetAccelFromString', '(label)',
        deprecated=True,
        body="""\
            accel = wx.AcceleratorEntry()
            accel.FromString(label)
            return accel
            """)

    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

