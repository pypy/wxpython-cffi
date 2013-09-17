#---------------------------------------------------------------------------
# Name:        etg/pen.py
# Author:      Robin Dunn
#
# Created:     31-Aug-2011
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "pen"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxPen', 'wxPenList', ]    
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    c = module.find('wxPen')
    assert isinstance(c, etgtools.ClassDef)
    tools.removeVirtuals(c)

    # The stipple bitmap ctor is not implemented on wxGTK
    c.find('wxPen').findOverload('wxBitmap').ignore()

    m = c.find('GetDashes')
    assert isinstance(m, etgtools.MethodDef)
    m.find('dashes').ignore()
    m.type = 'wxArrayInt*'
    m.factory = True
    m.setCppCode("""\
        wxArrayInt* arr = new wxArrayInt;
        wxDash* dashes;
        int num = self->GetDashes(&dashes);
        for (int i=0; i<num; i++)
            arr->Add(dashes[i]);
        return arr;
        """)

    
    c.addAutoProperties()

    # The stock Pen items are documented as simple pointers, but in reality
    # they are macros that evaluate to a function call that returns a pen
    # pointer, and that is only valid *after* the wx.App object has been
    # created. That messes up the code that SIP generates for them, so we need
    # to come up with another solution. So instead we will just create
    # uninitialized pens in a block of Python code, that will then be
    # intialized later when the wx.App is created.
    c.addCppMethod('void', '_copyFrom', '(const wxPen* other)', 
                   "*self = *other;",
                   briefDoc="For internal use only.")  # ??
    pycode = '# These stock pens will be initialized when the wx.App object is created.\n'
    for item in module:
        if '_PEN' in item.name:
            item.ignore()
            pycode += '%s = Pen()\n' % tools.removeWxPrefix(item.name)
    module.addPyCode(pycode)

    
    # it is delay-initialized, see stockgdi.sip
    module.find('wxThePenList').ignore()
    


    # Some aliases that should be phased out eventually, (sooner rather than
    # later.) They are already gone (or wrapped by an #if) in the C++ code,
    # and so are not found in the documentation...
    module.addPyCode("""\
        wx.SOLID       = int(wx.PENSTYLE_SOLID)
        wx.DOT         = int(wx.PENSTYLE_DOT) 
        wx.LONG_DASH   = int(wx.PENSTYLE_LONG_DASH)
        wx.SHORT_DASH  = int(wx.PENSTYLE_SHORT_DASH) 
        wx.DOT_DASH    = int(wx.PENSTYLE_DOT_DASH) 
        wx.USER_DASH   = int(wx.PENSTYLE_USER_DASH) 
        wx.TRANSPARENT = int(wx.PENSTYLE_TRANSPARENT) 
        """)

    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

