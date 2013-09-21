#---------------------------------------------------------------------------
# Name:        etg/graphics.py
# Author:      Kevin Ollivier
#              Robin Dunn
#
# Created:     10-Sept-2011
# Copyright:   (c) 2013 by Kevin Ollivier
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "graphics"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 
            'wxGraphicsObject',
            'wxGraphicsBitmap',
            'wxGraphicsBrush',
            'wxGraphicsFont',
            'wxGraphicsPen',
            'wxGraphicsContext',
            'wxGraphicsGradientStop',
            'wxGraphicsGradientStops',
            'wxGraphicsMatrix',
            'wxGraphicsPath',
            'wxGraphicsRenderer',
        ]
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)

    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.

    module.addHeaderCode('#include <wx/gdicmn.h>')
    
    def markFactories(klass):
        for func in klass.allItems():
            if isinstance(func, etgtools.FunctionDef) \
               and func.name.startswith('Create') \
               and '*' in func.type:
                func.factory = True

    #---------------------------------------------
    c = module.find('wxGraphicsObject')
    assert isinstance(c, etgtools.ClassDef)
    c.addCppMethod('bool', 'IsOk', '()', 'return !self->IsNull();')
    c.addCppMethod('int', '__nonzero__', '()', "return !self->IsNull();")


    #---------------------------------------------
    c = module.find('wxGraphicsContext')
    assert isinstance(c, etgtools.ClassDef)
    markFactories(c)
    tools.removeVirtuals(c)
    c.abstract = True

    # Ensure that the target DC or image lives as long as the GC does. NOTE:
    # Since the Creates are static methods there is no self to associate the
    # extra reference with, but since they are factories then that extra
    # reference will be held by the return value of the factory instead.
    for m in c.find('Create').all():
        for p in m.items:
            if 'DC' in p.name or p.name == 'image':
                p.keepReference = True
    
    
    # FIXME: Handle wxEnhMetaFileDC?
    c.find('Create').findOverload('wxEnhMetaFileDC').ignore()

    c.find('GetSize.width').out = True
    c.find('GetSize.height').out = True
    c.find('GetDPI.dpiX').out = True
    c.find('GetDPI.dpiY').out = True
    
    m = c.find('GetPartialTextExtents')
    m.find('widths').ignore()
    m.type = 'wxArrayDouble*'
    m.factory = True  # a new instance is being created
    m.setCppCode("""\
        wxArrayDouble rval;
        self->GetPartialTextExtents(*text, rval);
        return new wxArrayDouble(rval);
        """)
    
    m = c.find('GetTextExtent')
    m.pyName = 'GetFullTextExtent'
    m.find('width').out = True
    m.find('height').out = True
    m.find('descent').out = True
    m.find('externalLeading').out = True    
    
    c.addPyCode("GraphicsContext.DrawRotatedText = wx.deprecated(GraphicsContext.DrawText, 'Use DrawText instead.')")


    # we'll reimplement this overload as StrokeLineSegments
    c.find('StrokeLines').findOverload('beginPoints').ignore()

    # Also reimplement the main StrokeLines method to reuse the same helper
    # function as StrokLineSegments
    m = c.find('StrokeLines').findOverload('points').ignore()

    # and once more for DrawLines
    m = c.find('DrawLines').ignore()
    
    #---------------------------------------------
    c = module.find('wxGraphicsPath')
    tools.removeVirtuals(c)
    c.find('GetBox').findOverload('wxDouble *x, wxDouble *y').ignore()
    c.find('GetCurrentPoint').findOverload('wxDouble *x, wxDouble *y').ignore()
    
    
    #---------------------------------------------
    c = module.find('wxGraphicsRenderer')
    tools.removeVirtuals(c)
    markFactories(c)
    c.abstract = True
    
    for m in c.find('CreateContext').all():
        for p in m.items:
            if 'DC' in p.name or p.name == 'image':
                p.keepReference = True
    c.find('CreateContextFromImage.image').keepReference = True
    
    # FIXME: Handle wxEnhMetaFileDC?
    c.find('CreateContext').findOverload('wxEnhMetaFileDC').ignore()

  
    #---------------------------------------------
    c = module.find('wxGraphicsMatrix')
    tools.removeVirtuals(c)

    c.find('Concat').overloads = []
    c.find('IsEqual').overloads = []
    
    c.find('Get.a').out = True
    c.find('Get.b').out = True
    c.find('Get.c').out = True
    c.find('Get.d').out = True
    c.find('Get.tx').out = True
    c.find('Get.ty').out = True
    
    c.find('TransformDistance.dx').inOut = True
    c.find('TransformDistance.dy').inOut = True

    c.find('TransformPoint.x').inOut = True
    c.find('TransformPoint.y').inOut = True
    
    
    #---------------------------------------------
    c = module.find('wxGraphicsGradientStops')
    c.addCppMethod('SIP_SSIZE_T', '__len__', '()', body="return (SIP_SSIZE_T)self->GetCount();")
    c.addCppMethod('wxGraphicsGradientStop*', '__getitem__', '(size_t n)',
                   pyArgsString='(n)',
                   body="return new wxGraphicsGradientStop(self->Item(n));",
                   factory=True)

    
    #---------------------------------------------
    # Use the pyNames we set for these classes in geometry.py so the old
    # names do not show up in the docstrings, etc.
    tools.changeTypeNames(module, 'wxPoint2DDouble', 'wxPoint2D')
    tools.changeTypeNames(module, 'wxRect2DDouble', 'wxRect2D')
    

    tools.runGeneratorSpecificScript(module)

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

