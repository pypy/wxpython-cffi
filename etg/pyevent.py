#---------------------------------------------------------------------------
# Name:        etg/pyevent.py
# Author:      Robin Dunn
#
# Created:     02-Nov-2012
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools
from etgtools.extractors import ClassDef, MethodDef, ParamDef

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "pyevent"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS = [ ]

OTHERDEPS = [ "etg/sip/pyevent.py",
              "etg/cffi/pyevent.py",
            ]
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    tools.runGeneratorSpecificScript(module)
    
    cls = module.find('wxPyEvent')
    cls.addPyMethod('Clone', '(self)', 
        doc="""\
            Make a new instance of the event that is a copy of self.  
            
            Through the magic of Python this implementation should work for
            this and all derived classes.""",
        body="""\
            # Create a new instance
            import copy
            clone = copy.copy(self)
            # and then invoke the C++ copy constructor to copy the C++ bits too.
            wx.PyEvent.__init__(clone, self)
            return clone
            """)
    cls.addCppCode("IMPLEMENT_DYNAMIC_CLASS(wxPyEvent, wxEvent);")


    cls = module.find('wxPyCommandEvent')
    cls.addPyMethod('Clone', '(self)', 
        doc="""\
            Make a new instance of the event that is a copy of self.  
            
            Through the magic of Python this implementation should work for
            this and all derived classes.""",
        body="""\
            # Create a new instance
            import copy
            clone = copy.copy(self)
            # and then invoke the C++ copy constructor to copy the C++ bits too.
            wx.PyCommandEvent.__init__(clone, self)
            return clone
            """)
    cls.addCppCode("IMPLEMENT_DYNAMIC_CLASS(wxPyCommandEvent, wxCommandEvent);")
    
    
    
    # TODO: Temporary testing code, get rid of this later
    module.addCppCode("""\
        wxEvent* testCppClone(wxEvent& evt) {
            return evt.Clone();
        }""")
    #module.addItem(etgtools.WigCode("wxEvent* testCppClone(wxEvent& evt);"))
    module.addItem(etgtools.FunctionDef(
        type="wxEvent*", name="testCppClone", argsString="(wxEvent& evt)",
        items=[etgtools.ParamDef(type='wxEvent&', name='evt')]))
    

    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

