#---------------------------------------------------------------------------
# Name:        etg/dataobj.py
# Author:      Kevin Ollivier
#
# Created:     10-Sept-2011
# Copyright:   (c) 2013 by Kevin Ollivier
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "dataobj"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxDataFormat',
           'wxDataObject',
           'wxDataObjectSimple',
           'wxCustomDataObject',
           'wxDataObjectComposite',
           'wxBitmapDataObject',
           'wxTextDataObject',
           'wxURLDataObject',
           'wxFileDataObject',
           'wxHTMLDataObject',
           ]

   
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    c = module.find('wxDataFormat')
    assert isinstance(c, etgtools.ClassDef)
    c.find('GetType').setCppCode("return static_cast<wxDataFormatId>(self->GetType());")

    item = module.find('wxFormatInvalid')
    module.items.remove(item)
    module.insertItemAfter(c, item)
    
    
    #------------------------------------------------------------
    c = module.find('wxDataObject')
    c.addPrivateCopyCtor()

    # For initial testing only.  TODO: Remove later
    c.addPublic()
    c.addCppMethod('void', '_testGetAllFormats', '()',
        body="""\
            size_t count = self->GetFormatCount();
            wxDataFormat* fmts = new wxDataFormat[count];
            self->GetAllFormats(fmts);
            """)

   
   
    #------------------------------------------------------------
    c = module.find('wxDataObjectSimple')
    

    # We need to let SIP know that the pure virtuals in the base class have
    # impelmentations here even though they will not be used much (if at
    # all.) Those that are overridden in this class with different signatures
    # we'll just mark as private to help avoid confusion.
    #c.addItem(etgtools.WigCode(code="""\
    #    virtual size_t GetFormatCount(Direction dir = Get) const;
    #    virtual wxDataFormat GetPreferredFormat(Direction dir = Get) const;
    #    private:
    #    virtual size_t GetDataSize(const wxDataFormat& format) const;
    #    virtual bool GetDataHere(const wxDataFormat& format, void* buf) const;
    #    virtual bool SetData(const wxDataFormat& format, size_t len, const void* buf);
    #    """))
    c.addMethod('size_t', 'GetFormatCount', '(Direction dir = Get)',
                isConst=True, isVirtual=True)
    c.addMethod('wxDataFormat', 'GetPreferredFormat', '(Direction dir = Get)',
                isConst=True, isVirtual=True)
    
    #------------------------------------------------------------
    c = module.find('wxCustomDataObject')
    tools.removeVirtuals(c)

    # remove the methods having to do with allocating or owning the data buffer
    c.find('Alloc').ignore()
    c.find('Free').ignore()
    c.find('TakeData').ignore()


    #------------------------------------------------------------
    c = module.find('wxDataObjectComposite')

    c.find('Add.dataObject').transfer = True
    
    # The pure virtuals from wxDataObject have implementations here
    #c.addItem(etgtools.WigCode(code="""\
    #    virtual size_t GetFormatCount(Direction dir = Get) const;
    #    virtual wxDataFormat GetPreferredFormat(Direction dir = Get) const;
    #    private:
    #    virtual size_t GetDataSize(const wxDataFormat& format) const;
    #    virtual bool GetDataHere(const wxDataFormat& format, void* buf) const;
    #    virtual bool SetData(const wxDataFormat& format, size_t len, const void* buf);
    #    """))
    c.addMethod('size_t', 'GetFormatCount', '(Direction dir = Get)',
                isConst=True, isVirtual=True)
    c.addMethod('wxDataFormat', 'GetPreferredFormat', '(Direction dir = Get)',
                isConst=True, isVirtual=True)

    
    
    
    #------------------------------------------------------------
    c = module.find('wxURLDataObject')
    
    # wxURLDataObject derives from wxDataObjectComposite on some platforms,
    # and wxTextDataObject on others, so we need to take a least common
    # denominator approach here to be able to work on all platforms.
    c.bases = ['wxDataObject']
    
    #c.addItem(etgtools.WigCode(code="""\
    #    virtual size_t GetFormatCount(Direction dir = Get) const;
    #    virtual wxDataFormat GetPreferredFormat(Direction dir = Get) const;
    #    private:
    #    virtual size_t GetDataSize(const wxDataFormat& format) const;
    #    virtual bool GetDataHere(const wxDataFormat& format, void* buf) const;
    #    virtual bool SetData(const wxDataFormat& format, size_t len, const void* buf);
    #    """))
    c.addMethod('size_t', 'GetFormatCount', '(Direction dir = Get)',
                isConst=True, isVirtual=True)
    c.addMethod('wxDataFormat', 'GetPreferredFormat', '(Direction dir = Get)',
                isConst=True, isVirtual=True)

    

    #------------------------------------------------------------
    module.addPyCode("PyDataObjectSimple = wx.deprecated(DataObjectSimple), 'Use DataObjectSimple instead.'")
    module.addPyCode("PyTextDataObject = wx.deprecated(TextDataObject, 'Use TextDataObject instead.')")
    module.addPyCode("PyBitmapDataObject = wx.deprecated(BitmapDataObject, 'Use TextDataObject instead.')")

    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

