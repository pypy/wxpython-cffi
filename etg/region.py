#---------------------------------------------------------------------------
# Name:        etg/region.py
# Author:      Robin Dunn
#
# Created:     30-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "region"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ 'wxRegionIterator',
           'wxRegion'
           ]    
    
#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    
    c = module.find('wxRegion')
    assert isinstance(c, etgtools.ClassDef)
    tools.removeVirtuals(c)

    c.find('GetBox').findOverload('wxCoord').ignore()
    
    
    # Iterator stuff
    c.addPyMethod('__iter__', '(self)', 'return PyRegionIterator(self)',
                  """\
                  Returns a rectangle interator conforming to the Python iterator
                  protocol.""")
    c.addPyCode("""\
        class PyRegionIterator(object):
            "A Python iterator for wx.Region objects"
            def __init__(self, region):
                self._region = region
                self._iterator = wx.RegionIterator(region)
            def next(self):
                if not self._iterator:
                    raise StopIteration
                rect = self._iterator.GetRect()
                if self._iterator.HaveRects():
                    self._iterator.Next()
                return rect
            __next__ = next  # for Python 3
        """)
    


    c = module.find('wxRegionIterator')
    c.find('operator++').ignore()

    # SIP maps operator bool() to __int__, but Classic used __nonzero__. Does
    # it make any difference either way?
    c.find('operator bool').ignore()
    c.addCppMethod('int', '__nonzero__', '()', 'return (int)self->operator bool();',
                   'Returns true while there are still rectangles available in the iteration.')
    
    c.addCppMethod('void', 'Next', '()', 'self->operator++();',
                   'Move the iterator to the next rectangle in the region.')
    
    
    # This is defined in the docs, but not in any of the real headers!
    module.find('wxNullRegion').ignore()

    tools.runGeneratorSpecificScript(module)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

