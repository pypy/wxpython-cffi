#---------------------------------------------------------------------------
# Name:        etg/stattext.py
# Author:      Kevin Ollivier
#              Robin Dunn
#
# Created:     26-Aug-2011
# Copyright:   (c) 2013 by Wide Open Technologies
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "dc"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxFontMetrics',
           'wxDC', 
           'wxDCClipper',
           'wxDCBrushChanger',
           'wxDCPenChanger',
           'wxDCTextColourChanger',
           'wxDCFontChanger',
           ]    
    
OTHERDEPS = [ 'src/dc_ex.cpp', ]
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
            
    c = module.find('wxDC')
    assert isinstance(c, etgtools.ClassDef)

    c.addPrivateCopyCtor()
    c.addPublic()
    tools.removeVirtuals(c)
    
    # rename the more complex overload for these two, like in classic wxPython
    #c.find('GetTextExtent').findOverload('wxCoord *').pyName = 'GetFullTextExtent'
    #c.find('GetMultiLineTextExtent').findOverload('wxCoord *').pyName = 'GetFullMultiLineTextExtent'                   
    c.find('GetTextExtent').renameOverload('wxCoord *', 'GetFullTextExtent')
    c.find('GetMultiLineTextExtent').renameOverload('wxCoord *','GetFullMultiLineTextExtent')
    
    # Keep only the wxSize overloads of these
    c.find('GetSize').findOverload('wxCoord').ignore()
    c.find('GetSizeMM').findOverload('wxCoord').ignore()
    
    # TODO: needs wxAffineMatrix2D support.
    c.find('GetTransformMatrix').ignore()
    c.find('SetTransformMatrix').ignore()

    # remove wxPoint* overloads, we use the wxPointList ones
    c.find('DrawLines').findOverload('wxPoint points').ignore()
    c.find('DrawPolygon').findOverload('wxPoint points').ignore()
    c.find('DrawSpline').findOverload('wxPoint points').ignore()

    # TODO: we'll need a custom method implementation for this since there
    # are multiple array parameters involved...
    c.find('DrawPolyPolygon').ignore()


    
    # Add output param annotations so the generated docstrings will be correct
    c.find('GetUserScale.x').out = True
    c.find('GetUserScale.y').out = True

    c.find('GetLogicalScale.x').out = True
    c.find('GetLogicalScale.y').out = True
    
    c.find('GetLogicalOrigin').overloads = []
    c.find('GetLogicalOrigin.x').out = True
    c.find('GetLogicalOrigin.y').out = True
    
    c.find('GetFullTextExtent.w').out = True
    c.find('GetFullTextExtent.h').out = True
    c.find('GetFullTextExtent.descent').out = True
    c.find('GetFullTextExtent.externalLeading').out = True

    c.find('GetFullMultiLineTextExtent.w').out = True
    c.find('GetFullMultiLineTextExtent.h').out = True
    c.find('GetFullMultiLineTextExtent.heightLine').out = True
    
    c.find('GetClippingBox.x').out = True
    c.find('GetClippingBox.y').out = True
    c.find('GetClippingBox.width').out = True
    c.find('GetClippingBox.height').out = True
    c.addPyMethod('GetClippingRect', '(self)', 
        doc="Gets the rectangle surrounding the current clipping region",
        body="return wx.Rect(*self.GetClippingBox())")

    
    # Add some alternate implementations for DC methods, in order to avoid
    # using parameters as return values, etc. as well as Classic
    # compatibility.
    c.find('GetPixel').ignore()
    c.addCppMethod('wxColour*', 'GetPixel', '(wxCoord x, wxCoord y)', 
        doc="Gets the colour at the specified location on the DC.", body="""\
        wxColour* col = new wxColour;
        self->GetPixel(x, y, col);
        return col;
        """, factory=True)

    # Return the rect instead of using an output parameter
    m = c.find('DrawLabel').findOverload('rectBounding')
    m.type = 'wxRect*'
    m.find('rectBounding').ignore()
    m.factory = True  # a new instance of wxRect is being created
    m.setCppCode("""\
        wxRect rv;
        self->DrawLabel(*text, *bitmap, *rect, alignment, indexAccel, &rv);
        return new wxRect(rv);
        """)
    c.addPyCode('DC.DrawImageLabel = wx.deprecated(DC.DrawLabel, "Use DrawLabel instead.")')


    # Return the array instead of using an output parameter
    m = c.find('GetPartialTextExtents')
    m.type = 'wxArrayInt*'
    m.find('widths').ignore()
    m.factory = True  # a new instance is being created
    m.setCppCode("""\
        wxArrayInt rval;
        self->GetPartialTextExtents(*text, rval);
        return new wxArrayInt(rval);
        """)

    
    c.addCppMethod('int', '__nonzero__', '()', """\
        return self->IsOk();
        """)
   
    c.addPyMethod('GetBoundingBox', '(self)', doc="""\
        GetBoundingBox() -> (x1,y1, x2,y2)\n
        Returns the min and max points used in drawing commands so far.""",
        body="return (self.MinX(), self.MinY(), self.MaxX(), self.MaxY())")
    
    
    c.addCppMethod('long', 'GetHDC', '()', """\
        #ifdef __WXMSW__
            return (long)self->GetHandle();
        #else
            wxPyRaiseNotImplemented();
            return 0;
        #endif""")
    c.addCppMethod('void*', 'GetCGContext', '()', """\
        #ifdef __WXMAC__
            return self->GetHandle();
        #else
            wxPyRaiseNotImplemented();
            return NULL;
        #endif""")
    c.addCppMethod('void*', 'GetGdkDrawable', '()', """\
        #ifdef __WXGTK__
            return self->GetHandle();
        #else
            wxPyRaiseNotImplemented();
            return NULL;
        #endif""")
    
    c.addPyCode('DC.GetHDC = wx.deprecated(DC.GetHDC, "Use GetHandle instead.")')
    c.addPyCode('DC.GetCGContext = wx.deprecated(DC.GetCGContext, "Use GetHandle instead.")')
    c.addPyCode('DC.GetGdkDrawable = wx.deprecated(DC.GetGdkDrawable, "Use GetHandle instead.")')
    
    
    c.addPyMethod('DrawLineList', '(self, lines, pens=None)',
        doc="""\
            Draw a list of lines as quickly as possible.
    
            :param lines: A sequence of 4-element sequences representing
                          each line to draw, (x1,y1, x2,y2).
            :param pens:  If None, then the current pen is used.  If a
                          single pen then it will be used for all lines.  If
                          a list of pens then there should be one for each line
                          in lines.
            """,
        body="""\
            if pens is None:
                pens = []
            elif isinstance(pens, wx.Pen):
                pens = [pens]
            elif len(pens) != len(lines):
                raise ValueError('lines and pens must have same length')
            return self._DrawLineList(lines, pens, [])
            """)

    c.addPyMethod('DrawRectangleList', '(self, rectangles, pens=None, brushes=None)',
        doc="""\
            Draw a list of rectangles as quickly as possible.
    
            :param rectangles: A sequence of 4-element sequences representing
                               each rectangle to draw, (x,y, w,h).
            :param pens:       If None, then the current pen is used.  If a
                               single pen then it will be used for all rectangles.
                               If a list of pens then there should be one for each 
                               rectangle in rectangles.
            :param brushes:    A brush or brushes to be used to fill the rectagles,
                               with similar semantics as the pens parameter.
            """,
        body="""\
            if pens is None:
                pens = []
            elif isinstance(pens, wx.Pen):
                pens = [pens]
            elif len(pens) != len(rectangles):
                raise ValueError('rectangles and pens must have same length')
            if brushes is None:
                brushes = []
            elif isinstance(brushes, wx.Brush):
                brushes = [brushes]
            elif len(brushes) != len(rectangles):
                raise ValueError('rectangles and brushes must have same length')
            return self._DrawRectangleList(rectangles, pens, brushes)
            """)
    
    c.addPyMethod('DrawEllipseList', '(self, ellipses, pens=None, brushes=None)',
        doc="""\
            Draw a list of ellipses as quickly as possible.
    
            :param ellipses: A sequence of 4-element sequences representing
                             each ellipse to draw, (x,y, w,h).
            :param pens:     If None, then the current pen is used.  If a
                             single pen then it will be used for all ellipses.
                             If a list of pens then there should be one for each 
                             ellipse in ellipses.
            :param brushes:  A brush or brushes to be used to fill the ellipses,
                             with similar semantics as the pens parameter.
            """,
        body="""\
            if pens is None:
                pens = []
            elif isinstance(pens, wx.Pen):
                pens = [pens]
            elif len(pens) != len(ellipses):
                raise ValueError('ellipses and pens must have same length')
            if brushes is None:
                brushes = []
            elif isinstance(brushes, wx.Brush):
                brushes = [brushes]
            elif len(brushes) != len(ellipses):
                raise ValueError('ellipses and brushes must have same length')
            return self._DrawEllipseList(ellipses, pens, brushes)
            """)
    
    c.addPyMethod('DrawPolygonList', '(self, polygons, pens=None, brushes=None)',
        doc="""\
            Draw a list of polygons, each of which is a list of points.
    
            :param polygons: A sequence of sequences of sequences.
                             [[(x1,y1),(x2,y2),(x3,y3)...], [(x1,y1),(x2,y2),(x3,y3)...]]
                                  
            :param pens:     If None, then the current pen is used.  If a
                             single pen then it will be used for all polygons.
                             If a list of pens then there should be one for each 
                             polygon.
            :param brushes:  A brush or brushes to be used to fill the polygons,
                             with similar semantics as the pens parameter.
            """,
        body="""\
            if pens is None:
                pens = []
            elif isinstance(pens, wx.Pen):
                pens = [pens]
            elif len(pens) != len(polygons):
                raise ValueError('polygons and pens must have same length')
            if brushes is None:
                brushes = []
            elif isinstance(brushes, wx.Brush):
                brushes = [brushes]
            elif len(brushes) != len(polygons):
                raise ValueError('polygons and brushes must have same length')
            return self._DrawPolygonList(polygons, pens, brushes)
            """)
    
    c.addPyMethod('DrawTextList', '(self, textList, coords, foregrounds=None, backgrounds=None)',
        doc="""\
            Draw a list of strings using a list of coordinants for positioning each string.
    
            :param textList:    A list of strings
            :param coords:      A list of (x,y) positions
            :param foregrounds: A list of `wx.Colour` objects to use for the
                                foregrounds of the strings.
            :param backgrounds: A list of `wx.Colour` objects to use for the
                                backgrounds of the strings.
    
            NOTE: Make sure you set background mode to wx.Solid (DC.SetBackgroundMode)
                  If you want backgrounds to do anything.
            """,
        body="""\
            if type(textList) == type(''):
                textList = [textList]
            elif len(textList) != len(coords):
                raise ValueError('textlist and coords must have same length')
            if foregrounds is None:
                foregrounds = []
            elif isinstance(foregrounds, wx.Colour):
                foregrounds = [foregrounds]
            elif len(foregrounds) != len(coords):
                raise ValueError('foregrounds and coords must have same length')
            if backgrounds is None:
                backgrounds = []
            elif isinstance(backgrounds, wx.Colour):
                backgrounds = [backgrounds]
            elif len(backgrounds) != len(coords):
                raise ValueError('backgrounds and coords must have same length')
            return  self._DrawTextList(textList, coords, foregrounds, backgrounds)
            """)




    # TODO: Port the PseudoDC from Classic


    
    #-----------------------------------------------------------------
    c = module.find('wxDCClipper')
    assert isinstance(c, etgtools.ClassDef)
    c.addPrivateCopyCtor()
    # context manager methods
    c.addPyMethod('__enter__', '(self)', 'return self')
    c.addPyMethod('__exit__', '(self, exc_type, exc_val, exc_tb)', 'return False')

    
    #-----------------------------------------------------------------
    c = module.find('wxDCBrushChanger')
    assert isinstance(c, etgtools.ClassDef)
    c.addPrivateCopyCtor()
    # context manager methods
    c.addPyMethod('__enter__', '(self)', 'return self')
    c.addPyMethod('__exit__', '(self, exc_type, exc_val, exc_tb)', 'return False')

    
    #-----------------------------------------------------------------
    c = module.find('wxDCPenChanger')
    assert isinstance(c, etgtools.ClassDef)
    c.addPrivateCopyCtor()
    # context manager methods
    c.addPyMethod('__enter__', '(self)', 'return self')
    c.addPyMethod('__exit__', '(self, exc_type, exc_val, exc_tb)', 'return False')

    
    #-----------------------------------------------------------------
    c = module.find('wxDCTextColourChanger')
    assert isinstance(c, etgtools.ClassDef)
    c.addPrivateCopyCtor()
    # context manager methods
    c.addPyMethod('__enter__', '(self)', 'return self')
    c.addPyMethod('__exit__', '(self, exc_type, exc_val, exc_tb)', 'return False')

    
    #-----------------------------------------------------------------
    c = module.find('wxDCFontChanger')
    assert isinstance(c, etgtools.ClassDef)
    c.addPrivateCopyCtor()
    # context manager methods
    c.addPyMethod('__enter__', '(self)', 'return self')
    c.addPyMethod('__exit__', '(self, exc_type, exc_val, exc_tb)', 'return False')
    
    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

