#---------------------------------------------------------------------------
# Name:        etg/gdicmn.py
# Author:      Robin Dunn
#
# Created:     4-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "gdicmn"
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [  'wxPoint',
            'wxSize',
            'wxRect',
            'wxRealPoint',
            'wxColourDatabase',
            ]
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    
    # ignore some of these enum values
    e = module.find('wxBitmapType')
    for i in e:
        if i.name.endswith('_RESOURCE'):
            i.ignore()
    
    module.addCppCode("""\
    #if !defined(__WXMAC__)
    #define wxCURSOR_COPY_ARROW wxCURSOR_ARROW
    #endif
    """)
    
    # these are X11 only
    e = module.find('wxStockCursor')
    e.find('wxCURSOR_BASED_ARROW_DOWN').ignore()
    e.find('wxCURSOR_BASED_ARROW_UP').ignore()
    e.find('wxCURSOR_CROSS_REVERSE').ignore()
    e.find('wxCURSOR_DOUBLE_ARROW').ignore()
    
    module.find('wxClientDisplayRect.x').out = True
    module.find('wxClientDisplayRect.y').out = True
    module.find('wxClientDisplayRect.width').out = True
    module.find('wxClientDisplayRect.height').out = True
    
    module.find('wxDisplaySize.width').out = True
    module.find('wxDisplaySize.height').out = True
    module.find('wxDisplaySizeMM.width').out = True
    module.find('wxDisplaySizeMM.height').out = True
    
    #---------------------------------------
    # wxPoint tweaks
    c = module.find('wxPoint')
    tools.addAutoProperties(c)
    
    # Some operators are documented within the class that shouldn't be, so just
    # ignore them all.
    tools.ignoreAllOperators(c)
    
    # Undo a few of those ignores for legitimate items that were 
    # documented correctly
    for f in c.find('operator+=').all() + c.find('operator-=').all():
        f.ignore(False)
        
    # Add some method declarations for operators that really do exist. Note
    # that these actually use C++ global operator functions, but we treat
    # them as methods to help disambiguate implementations due to how
    # multiple classes can be converted automatically to/from 2-element
    # sequences.    
    c.addCppMethod('bool', '__eq__', '(const wxPoint& other)',
        body="return *self == *other;")
    c.addCppMethod('bool', '__neq__', '(const wxPoint& other)',
        body="return *self != *other;")
    
    # TODO: replace these with MethodDefs
    #c.addItem(etgtools.WigCode("""\
    #    wxPoint operator+(const wxPoint& other);
    #    wxPoint operator-();
    #    wxPoint operator-(const wxPoint& other);
    #    wxPoint operator*(int i);
    #    wxPoint operator/(int i);
    #    """))

    c.addMethod(
        'wxPoint', 'operator+', '(const wxPoint& other)',
        items=[etgtools.ParamDef(type='const wxPoint&', name='other')])
    c.addMethod(
        'wxPoint', 'operator-', '(const wxPoint& other)',
        items=[etgtools.ParamDef(type='const wxPoint&', name='other')])
    c.addMethod('wxPoint', 'operator-', '()')
    c.addMethod(
        'wxPoint', 'operator*', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])
    c.addMethod(
        'wxPoint', 'operator/', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])
    
    
    # wxPoint typemap
    c.convertFromPyObject = tools.convertTwoIntegersTemplate('wxPoint')
    tools.convertTwoIntegersTemplate_cffi(c)
    
    # Add sequence protocol methods and other goodies
    c.addPyMethod('__str__', '(self)',             'return str(self.Get())')
    c.addPyMethod('__repr__', '(self)',            'return "wx.Point"+str(self.Get())')
    c.addPyMethod('__len__', '(self)',             'return len(self.Get())')
    c.addPyMethod('__nonzero__', '(self)',         'return self.Get() != (0,0)')
    c.addPyMethod('__reduce__', '(self)',          'return (Point, self.Get())')
    c.addPyMethod('__getitem__', '(self, idx)',    'return self.Get()[idx]')
    c.addPyMethod('__setitem__', '(self, idx, val)',
                  """\
                  if idx == 0: self.x = val
                  elif idx == 1: self.y = val
                  else: raise IndexError
                  """) 
    c.addPyCode('Point.__safe_for_unpickling__ = True')
                                    
    # TODO: how do I handle this?
    module.addItem(
        tools.wxListWrapperTemplate('wxPointList', 'wxPoint', module, includeConvertToType=True))
    
    
    #---------------------------------------
    # wxSize tweaks
    c = module.find('wxSize')
    tools.addAutoProperties(c)

    # Used for testing releasing or holding the GIL in giltest.py
    #c.find('wxSize').findOverload('int width, int height').releaseGIL()
    #c.find('DecBy').findOverload('int dx, int dy').releaseGIL()
    #c.find('IncBy').findOverload('int dx, int dy').releaseGIL()
        
    c.addProperty("width GetWidth SetWidth")
    c.addProperty("height GetHeight SetHeight")

    # TODO:  How prevalent is the use of x,y properties on a size object?  Can we deprecate them?
    c.addProperty("x GetWidth SetWidth")
    c.addProperty("y GetHeight SetHeight")
    
    # Take care of the same issues as wxPoint
    tools.ignoreAllOperators(c)
    for f in c.find('operator+=').all() + \
             c.find('operator-=').all() + \
             c.find('operator*=').all() + \
             c.find('operator/=').all():
        f.ignore(False)
        
    c.addCppMethod('bool', '__eq__', '(const wxSize& other)',
        body="return *self == *other;")
    c.addCppMethod('bool', '__neq__', '(const wxSize& other)',
        body="return *self != *other;")
    
    # TODO: replace these with Method Defs
    #c.addItem(etgtools.WigCode("""\
    #    wxSize operator+(const wxSize& other);
    #    wxSize operator-(const wxSize& other);
    #    wxSize operator*(int i);
    #    wxSize operator/(int i);

    #    wxPoint operator+(const wxPoint& other);
    #    wxPoint operator-(const wxPoint& other);
    #    wxRealPoint operator+(const wxRealPoint& other);
    #    wxRealPoint operator-(const wxRealPoint& other);
    #    """))

    c.addMethod(
        'wxSize', 'operator+', '(const wxSize& other)',
        items=[etgtools.ParamDef(type='const wxSize&', name='other')])
    c.addMethod(
        'wxSize', 'operator-', '(const wxSize& other)',
        items=[etgtools.ParamDef(type='const wxSize&', name='other')])
    c.addMethod(
        'wxSize', 'operator*', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])
    c.addMethod(
        'wxSize', 'operator/', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])

    c.addMethod(
        'wxPoint', 'operator+', '(const wxPoint& other)',
        items=[etgtools.ParamDef(type='const wxPoint&', name='other')])
    c.addMethod(
        'wxPoint', 'operator-', '(const wxPoint& other)',
        items=[etgtools.ParamDef(type='const wxPoint&', name='other')])
    c.addMethod(
        'wxRealPoint', 'operator+', '(const wxRealPoint& other)',
        items=[etgtools.ParamDef(type='const wxRealPoint&', name='other')])
    c.addMethod(
        'wxRealPoint', 'operator-', '(const wxRealPoint& other)',
        items=[etgtools.ParamDef(type='const wxRealPoint&', name='other')])
    
    
    # wxSize typemap
    c.convertFromPyObject = tools.convertTwoIntegersTemplate('wxSize')
    tools.convertTwoIntegersTemplate_cffi(c)
    
    # Add sequence protocol methods and other goodies
    c.addPyMethod('__str__', '(self)',             'return str(self.Get())')
    c.addPyMethod('__repr__', '(self)',            'return "wx.Size"+str(self.Get())')
    c.addPyMethod('__len__', '(self)',             'return len(self.Get())')
    c.addPyMethod('__nonzero__', '(self)',         'return self.Get() != (0,0)')
    c.addPyMethod('__reduce__', '(self)',          'return (Size, self.Get())')
    c.addPyMethod('__getitem__', '(self, idx)',    'return self.Get()[idx]')
    c.addPyMethod('__setitem__', '(self, idx, val)',
                  """\
                  if idx == 0: self.width = val
                  elif idx == 1: self.height = val
                  else: raise IndexError
                  """) 
    c.addPyCode('Size.__safe_for_unpickling__ = True')
    
    
    
    #---------------------------------------
    # wxRect tweaks
    c = module.find('wxRect')
    assert isinstance(c, etgtools.ClassDef)
    tools.addAutoProperties(c)
    
    c.addProperty("left GetLeft SetLeft")
    c.addProperty("top GetTop SetTop")
    c.addProperty("right GetRight SetRight")
    c.addProperty("bottom GetBottom SetBottom")
    
    c.addProperty("bottomLeft GetBottomLeft SetBottomLeft")
    c.addProperty("bottomRight GetBottomRight SetBottomRight")
    c.addProperty("topLeft GetTopLeft SetTopLeft")
    c.addProperty("topRight GetTopRight SetTopRight")
    
    # take care of the same issues as wxPoint
    tools.ignoreAllOperators(c)
    for f in c.find('operator+=').all() + \
             c.find('operator*=').all():
        f.ignore(False)
                
    c.addCppMethod('bool', '__eq__', '(const wxRect& other)',
        body="return *self == *other;")
    c.addCppMethod('bool', '__neq__', '(const wxRect& other)',
        body="return *self != *other;")
    
    # TODO: replace these with MethodDefs
    #c.addItem(etgtools.WigCode("""\
    #    wxRect operator+(const wxRect& other);
    #    wxRect operator*(const wxRect& other);
    #    """))

    c.addMethod(
        'wxRect', 'operator+', '(const wxRect& other)',
        items=[etgtools.ParamDef(type='const wxRect&', name='other')])
    c.addMethod(
        'wxRect', 'operator*', '(const wxRect& other)',
        items=[etgtools.ParamDef(type='const wxRect&', name='other')])

    
    # Because of our add-ons that make wx.Point and wx.Size act like 2-element
    # sequences, and also the typecheck code that allows 2-element sequences, then
    # we end up with a bit of confusion about the (Point,Point) and the
    # (Point,Size) overloads of the wx.Rect constructor. The confusion can be
    # dealt with by using keyword args, but I think that the (Point,Size) version
    # will be used more, so reorder the overloads so it is found first.
    m = module.find('wxRect.wxRect')
    mo = m.findOverload('topLeft')
    del m.overloads[m.overloads.index(mo)]
    m.overloads.append(mo)
    
    # These methods have some overloads that will end up with the same signature
    # in Python, so we have to remove one.
    module.find('wxRect.Deflate').findOverload(') const').ignore()
    module.find('wxRect.Inflate').findOverload(') const').ignore()
    module.find('wxRect.Union').findOverload(') const').ignore()
    module.find('wxRect.Intersect').findOverload(') const').ignore()
    
    # wxRect typemap
    c.convertFromPyObject = tools.convertFourIntegersTemplate('wxRect')
    tools.convertFourIntegersTemplate_cffi(c)
    
    # Add sequence protocol methods and other goodies
    c.addPyMethod('__str__', '(self)',             'return str(self.Get())')
    c.addPyMethod('__repr__', '(self)',            'return "wx.Rect"+str(self.Get())')
    c.addPyMethod('__len__', '(self)',             'return len(self.Get())')
    c.addPyMethod('__nonzero__', '(self)',         'return self.Get() != (0,0,0,0)')
    c.addPyMethod('__reduce__', '(self)',          'return (Rect, self.Get())')
    c.addPyMethod('__getitem__', '(self, idx)',    'return self.Get()[idx]')
    c.addPyMethod('__setitem__', '(self, idx, val)',
                  """\
                  if idx == 0: self.x = val
                  elif idx == 1: self.y = val
                  elif idx == 2: self.width = val
                  elif idx == 3: self.height = val
                  else: raise IndexError
                  """) 
    c.addPyCode('Rect.__safe_for_unpickling__ = True')
    
    
    
    #---------------------------------------
    # wxRealPoint tweaks
    c = module.find('wxRealPoint')
    tools.addAutoProperties(c)
        
    # take care of the same issues as wxPoint
    tools.ignoreAllOperators(c)
    for f in c.find('operator+=').all() + \
             c.find('operator-=').all():
        f.ignore(False)
                
    c.addCppMethod('bool', '__eq__', '(const wxRealPoint& other)',
        body="return *self == *other;")
    c.addCppMethod('bool', '__neq__', '(const wxRealPoint& other)',
        body="return *self != *other;")
    
    # TODO: replace these with MethodDefs
    #c.addItem(etgtools.WigCode("""\
    #    wxRealPoint operator+(const wxRealPoint& other);
    #    wxRealPoint operator-(const wxRealPoint& other);
    #    wxRealPoint operator*(int i);
    #    wxRealPoint operator/(int i);
    #    """))

    c.addMethod(
        'wxRealPoint', 'operator+',
        '(const wxRealPoint& other)',
        items=[etgtools.ParamDef(type='const wxRealPoint&', name='other')])
    c.addMethod(
        'wxRealPoint', 'operator-',
        '(const wxRealPoint& other)',
        items=[etgtools.ParamDef(type='const wxRealPoint&', name='other')])
    c.addMethod(
        'wxRealPoint', 'operator*', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])
    c.addMethod(
        'wxRealPoint', 'operator/', '(int i)',
        items=[etgtools.ParamDef(type='int', name='i')])

        
    # wxRealPoint typemap
    c.convertFromPyObject = tools.convertTwoDoublesTemplate('wxRealPoint')
    tools.convertTwoDoublesTemplate_cffi(c)

    # Add sequence protocol methods and other goodies
    c.addPyMethod('__str__', '(self)',             'return str(self.Get())')
    c.addPyMethod('__repr__', '(self)',            'return "wx.RealPoint"+str(self.Get())')
    c.addPyMethod('__len__', '(self)',             'return len(self.Get())')
    c.addPyMethod('__nonzero__', '(self)',         'return self.Get() != (0,0)')
    c.addPyMethod('__reduce__', '(self)',          'return (Rect, self.Get())')
    c.addPyMethod('__getitem__', '(self, idx)',    'return self.Get()[idx]')
    c.addPyMethod('__setitem__', '(self, idx, val)',
                  """\
                  if idx == 0: self.x = val
                  elif idx == 1: self.y = val
                  else: raise IndexError
                  """) 
    c.addPyCode('RealPoint.__safe_for_unpickling__ = True')

    
    
    
    c = module.find('wxColourDatabase')
    c.addPyMethod('FindColour', '(self, colour)',    'return self.Find(colour)')   

    module.find('wxTheColourDatabase').ignore()
        
    tools.runGeneratorSpecificScript(module)
                               
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

