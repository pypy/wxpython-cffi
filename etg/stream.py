#---------------------------------------------------------------------------
# Name:        etg/stream.py
# Author:      Robin Dunn
#
# Created:     18-Nov-2011
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "stream"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxStreamBase',
           'wxInputStream',
           'wxOutputStream',
           ]    

    
OTHERDEPS = [ 'src/stream_input.cpp',
              'src/stream_output.cpp',
              ]

#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)

    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.

    # These enums are declared in files that we will not be using because
    # wxPython does not need the classes that are in those files. So just
    # inject the enums here instead.
    from etgtools import EnumDef, EnumValueDef
    e = EnumDef(name='wxStreamError')
    e.items.extend([ EnumValueDef(name='wxSTREAM_NO_ERROR'),
                     EnumValueDef(name='wxSTREAM_EOF'),
                     EnumValueDef(name='wxSTREAM_WRITE_ERROR'),
                     EnumValueDef(name='wxSTREAM_READ_ERROR'),
                     ])
    module.insertItem(0, e)
    
    e = EnumDef(name='wxSeekMode')
    e.items.extend([ EnumValueDef(name='wxFromStart'),
                     EnumValueDef(name='wxFromCurrent'),
                     EnumValueDef(name='wxFromEnd'),
                     ])
    module.insertItem(1, e)
    
    
    #-----------------------------------------------------------------
    c = module.find('wxStreamBase')
    assert isinstance(c, etgtools.ClassDef)
    c.abstract = True
    tools.removeVirtuals(c)
    c.find('operator!').ignore()
    
    
    #-----------------------------------------------------------------
    c = module.find('wxInputStream')
    c.abstract = True
    tools.removeVirtuals(c)

    # Use that class for the convert code
    c.convertFromPyObject = """\
        // is it just a typecheck?
        if (!sipIsErr) {
            if (wxPyInputStream::Check(sipPy))
                return 1;
            return 0;
        }
        // otherwise do the conversion
        *sipCppPtr = new wxPyInputStream(sipPy);
        return sipGetState(sipTransferObj);
        """



    # Add Python file-like methods so a wx.InputStream can be used as if it
    # was any other Python file object.
    c.addCppMethod('void', 'seek', '(wxFileOffset offset, int whence=0)', """\
        self->SeekI(offset, (wxSeekMode)whence);
        """)
    c.addCppMethod('wxFileOffset', 'tell', '()', """\
        return self->TellI();
        """);
    c.addCppMethod('void', 'close', '()', """\
        // ignored for now
        """)
    c.addCppMethod('void', 'flush', '()', """\
        // ignored for now
        """)
    c.addCppMethod('bool', 'eof', '()', """\
        return self->Eof();
        """)
    
    #-----------------------------------------------------------------
    c = module.find('wxOutputStream')
    c.abstract = True
    tools.removeVirtuals(c)


    # Use that class for the convert code
    c.convertFromPyObject = """\
        // is it just a typecheck?
        if (!sipIsErr) {
            if (wxPyOutputStream::Check(sipPy))
                return 1;
            return 0;
        }
        // otherwise do the conversion
        *sipCppPtr = new wxPyOutputStream(sipPy);
        return sipGetState(sipTransferObj);
        """

    # Add Python file-like methods so a wx.OutputStream can be used as if it
    # was any other Python file object.
    c.addCppMethod('void', 'seek', '(wxFileOffset offset, int whence=0)', """\
        self->SeekO(offset, (wxSeekMode)whence);
        """)
    c.addCppMethod('wxFileOffset', 'tell', '()', """\
        return self->TellO();
        """);
    c.addCppMethod('void', 'close', '()', """\
        self->Close();
        """)
    c.addCppMethod('void', 'flush', '()', """\
        self->Sync();
        """)
    c.addCppMethod('bool', 'eof', '()', """\
        return false; //self->Eof();
        """)

    # TODO: Add a writelines(sequence) method
    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

