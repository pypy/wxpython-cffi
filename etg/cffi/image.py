import etgtools
import etgtools.tweaker_tools as tools

def run(module):
    c = module.find('wxImage')
    # TODO: Add wxPyBuffer Ctors

    # GetData() and GetAlpha() return a copy of the image data/alpha bytes as
    # a bytearray object. 
    c.find('GetData').ignore()
    c.find('GetAlpha').findOverload('()').ignore()
    # TODO: add CppMethodDef_cffis for GetData and GetAlpha

    module.addItem(etgtools.ClassDef(name='wxPalette'))
