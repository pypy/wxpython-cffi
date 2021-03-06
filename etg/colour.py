#---------------------------------------------------------------------------
# Name:        etc/colour.py
# Author:      Robin Dunn
#
# Created:     19-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "colour"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxColour' ]    

OTHERDEPS = [ 'etg/cffi/colour.py' ]
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    
    # Add a ctor/factory for the Mac that can use the theme brush
    module.addCppCode("""\
    #ifdef __WXMAC__
    #include <wx/osx/private.h>
    #endif
    """)    
    module.addCppFunction('wxColour*', 'MacThemeColour', '(int themeBrushID)', """\
    #ifdef __WXMAC__
        return new wxColour(wxMacCreateCGColorFromHITheme(themeBrushID));
    #else
        wxPyRaiseNotImplemented(); 
        return NULL; 
    #endif
    """, factory=True)
    
    
    # Change this macro into a value so we wont have problems when SIP takes its
    # address
    module.addCppCode("""\
    #undef wxTransparentColour
    wxColour wxTransparentColour(0, 0, 0, wxALPHA_TRANSPARENT);
    """)
    
    
    module.find('wxFromString').ignore()
    module.find('wxToString').ignore()
        
    module.find('wxALPHA_TRANSPARENT').type = 'const int'
    module.find('wxALPHA_OPAQUE').type = 'const int'
        
    
        
    c = module.find('wxColour')
    assert isinstance(c, etgtools.ClassDef)
    tools.removeVirtuals(c)
    
    # Hide the string ctor so our typemap will be invoked for the copy ctor instead.
    c.find('wxColour').findOverload('wxString').ignore()
    
    c.addProperty('Pixel GetPixel')
    c.addProperty('RGB GetRGB SetRGB')
    c.addProperty('RGBA GetRGBA SetRGBA')
    c.addProperty('red Red')
    c.addProperty('green Green')
    c.addProperty('blue Blue')
    c.addProperty('alpha Alpha')
    
    c.find('GetPixel').ignore()  # We need to add a typcast
    c.addCppMethod('wxIntPtr', 'GetPixel', '()', """\
        #ifdef __WXGTK3__
            return 0;
        #else
            return (wxIntPtr)self->GetPixel();
        #endif
        """)
        
    # Set a flag on the return value and parameter types that are 'unsigned char'
    # such that they will be treated as an integer instead of a string. 
    for item in c.allItems():
        if hasattr(item, 'type') and item.type == 'unsigned char':
            item.pyInt = True
            
    
    c.find('ChangeLightness.r').inOut = True
    c.find('ChangeLightness.g').inOut = True
    c.find('ChangeLightness.b').inOut = True
    
    c.find('MakeDisabled.r').inOut = True
    c.find('MakeDisabled.g').inOut = True
    c.find('MakeDisabled.b').inOut = True
    
    c.find('MakeGrey.r').inOut = True
    c.find('MakeGrey.g').inOut = True
    c.find('MakeGrey.b').inOut = True
    c.find('MakeGrey').findOverload('double').find('r').inOut = True
    c.find('MakeGrey').findOverload('double').find('g').inOut = True
    c.find('MakeGrey').findOverload('double').find('b').inOut = True
    
    c.find('MakeMono.r').out = True
    c.find('MakeMono.g').out = True
    c.find('MakeMono.b').out = True
    
    
    # The stock Colour items are documented as simple pointers, but in
    # reality they are macros that evaluate to a function call that returns a
    # Colour pointer, and that is only valid *after* the wx.App object has
    # been created. That messes up the code that SIP generates for them. So
    # instead we will just create uninitialized colour in a block of Python
    # code, that will then be intialized later when the wx.App is created.
    c.addCppMethod('void', '_copyFrom', '(const wxColour* other)', 
                   "*self = *other;",
                   briefDoc="For internal use only.")  # ??
    pycode = '# These stock colours will be initialized when the wx.App object is created.\n'
    for name in [ 'wxBLACK',
                  'wxBLUE',             
                  'wxCYAN',
                  'wxGREEN',
                  'wxYELLOW',
                  'wxLIGHT_GREY',
                  'wxRED',
                  'wxWHITE',
                  ]:
        item = module.find(name)
        item.ignore()
        pycode += '%s = Colour()\n' % tools.removeWxPrefix(item.name)
    module.addPyCode(pycode)

    
        
    # Add sequence protocol methods and other goodies
    c.addPyMethod('__str__', '(self)',             'return str(self.Get())')
    c.addPyMethod('__repr__', '(self)',            'return "wx.Colour"+str(self.Get())')
    c.addPyMethod('__len__', '(self)',             'return len(self.Get())')
    c.addPyMethod('__nonzero__', '(self)',         'return self.IsOk()')
    c.addPyMethod('__reduce__', '(self)',          'return (Colour, self.Get())')
    c.addPyMethod('__getitem__', '(self, idx)',    'return self.Get()[idx]')
    c.addPyMethod('__setitem__', '(self, idx, val)',
                  """\
                  if idx == 0:   self.red = val
                  elif idx == 1: self.green = val
                  elif idx == 2: self.blue = val
                  elif idx == 3: self.alpha = val
                  else: raise IndexError
                  """) 
    c.addPyCode('Colour.__safe_for_unpickling__ = True')

    # Types that can be converted to wx.Colour:
    #     wxColour (duh)
    #     Sequence with 3 or 4 integers
    #     String with color name or #RRGGBB or #RRGGBBAA format
    #     None  (converts to wxNullColour)
    c.allowNone = True
    c.convertFromPyObject = """\
        // is it just a typecheck?
        if (!sipIsErr) {
            if (sipPy == Py_None)
                return 1;
            if (sipCanConvertToType(sipPy, sipType_wxColour, SIP_NO_CONVERTORS))
                return 1;
            if (PyBytes_Check(sipPy) || PyUnicode_Check(sipPy))
                return 1;           
            if (PySequence_Check(sipPy)) {
                size_t len = PySequence_Size(sipPy);
                if (len != 3 && len != 4) 
                    return 0;
                // ensure all the items in the sequence are numbers
                for (int idx=0; idx<len; idx+=1) {
                    PyObject* o = PySequence_ITEM(sipPy, idx);
                    bool isNum = PyNumber_Check(o);
                    Py_DECREF(o);
                    if (!isNum)
                        return 0;
                }
                return 1;
            }
            return 0;
        }
        // otherwise do the conversion
        // is it None?
        if (sipPy == Py_None) {
            *sipCppPtr = new wxColour(wxNullColour);
            return sipGetState(sipTransferObj);
        }
        // Is it a string?
        else if (PyBytes_Check(sipPy) || PyUnicode_Check(sipPy)) {
            wxString spec = Py2wxString(sipPy);
            if (!spec.empty() 
                && spec.GetChar(0) == '#' 
                && (spec.length() == 7 || spec.length() == 9)) {  // It's  #RRGGBB[AA]
                long red, green, blue;
                red = green = blue = 0;
                spec.Mid(1,2).ToLong(&red,   16);
                spec.Mid(3,2).ToLong(&green, 16);
                spec.Mid(5,2).ToLong(&blue,  16);
    
                if (spec.length() == 7)         // no alpha
                    *sipCppPtr = new wxColour(red, green, blue);
                else {                          // yes alpha
                    long alpha;
                    spec.Mid(7,2).ToLong(&alpha, 16);
                    *sipCppPtr = new wxColour(red, green, blue, alpha);
                }
                return sipGetState(sipTransferObj);
            }
            else {                                       // assume it's a colour name
                // check if alpha is there too
                int pos;
                if (((pos = spec.Find(':', true)) != wxNOT_FOUND) && (pos == spec.length()-3)) {
                    long alpha;
                    spec.Right(2).ToLong(&alpha, 16);
                    wxColour c = wxColour(spec.Left(spec.length()-3));
                    *sipCppPtr = new wxColour(c.Red(), c.Green(), c.Blue(), alpha);
                }
                else
                    *sipCppPtr = new wxColour(spec);
                return sipGetState(sipTransferObj);
            }
        }
        // Is it a 3 or 4 element sequence?
        else if (PySequence_Check(sipPy)) {
            size_t len = PyObject_Length(sipPy);
            
            PyObject* o1 = PySequence_GetItem(sipPy, 0);
            PyObject* o2 = PySequence_GetItem(sipPy, 1);
            PyObject* o3 = PySequence_GetItem(sipPy, 2);
            if (len == 3) 
                *sipCppPtr = new wxColour(wxPyInt_AsLong(o1), wxPyInt_AsLong(o2), wxPyInt_AsLong(o3));
            else {
                PyObject* o4 = PySequence_GetItem(sipPy, 3);
                *sipCppPtr = new wxColour(wxPyInt_AsLong(o1), wxPyInt_AsLong(o2), wxPyInt_AsLong(o3),
                                          wxPyInt_AsLong(o4));
                Py_DECREF(o4);
            }
            Py_DECREF(o1);
            Py_DECREF(o2);
            Py_DECREF(o3);
            return sipGetState(sipTransferObj);
        }
    
        // if we get this far then it must already be a wxColour instance
        *sipCppPtr = reinterpret_cast<wxColour*>(sipConvertToType(
            sipPy, sipType_wxColour, sipTransferObj, SIP_NO_CONVERTORS, 0, sipIsErr));
        return 0; // not a new instance
    """
    c.convertFromPyObject_cffi = """\
    if py_obj is None:
        return NullColour

    if isinstance(py_obj, (str, unicode)):
        if py_obj[0] == '#' and (len(py_obj) == 7 or len(py_obj) == 9):
            try:
                red = int(py_obj[1:3], 16)
            except ValueError:
                red = 0
            try:
                green = int(py_obj[3:5], 16)
            except ValueError:
                green = 0
            try:
                blue = int(py_obj[5:7], 16)
            except ValueError:
                blue = 0

            if len(py_obj) == 7:
                return Colour(red, green, blue)
            else:
                try:
                    alpha = int(py_obj[7:9], 16)
                except ValueError:
                    alpha = 255
                return Colour(red, green, blue, alpha)

        pos = py_obj.find(':')
        if pos != -1:
            try:
                alpha = int(py_obj[pos + 1:], 16)
            except ValueError:
                alpha = 255
            c = Colour._fromString(py_obj[:pos])
            c.Set(c.Red(), c.Green(), c.Blue(), alpha)
            return c
        else:
            return Colour._fromString(py_obj)

    if len(py_obj) == 3:
        return Colour(py_obj[0], py_obj[1], py_obj[2])
    return Colour(py_obj[0], py_obj[1], py_obj[2], py_obj[3])
    """
    c.instanceCheck_cffi = """\
    if py_obj is None or isinstance(py_obj, (str, unicode)):
        return True
    if not isinstance(py_obj, collections.Sequence):
        return False

    obj_len = len(py_obj)
    if not (obj_len == 3 or obj_len == 4):
        return False
    return ((obj_len == 3 or obj_len == 4) and
            all([isinstance(py_obj[i], numbers.Number) for i in range(obj_len)]))
    """

    module.addPyCode('NamedColour = wx.deprecated(Colour, "Use Colour instead.")')
        
    
    # Just for TESTING, remove it later
    module.addCppCode("""\
    wxColour testColourTypeMap(const wxColour& c)
    {
        return c;
    }
    """)
    module.addItem(etgtools.FunctionDef(
        type='wxColour', name='testColourTypeMap', argsString='(const wxColour& c)',
        items=[etgtools.ParamDef(type='const wxColour&', name='c')], isCore=True))
    

    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
   
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

