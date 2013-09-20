def run(module):
    c = module.find('wxPyApp')

    # Add a new C++ wxPyApp class that adds empty Mac* methods for other
    # platforms, and other goodies, then change the name so SIP will
    # generate code wrapping this class as if it was the wxApp class seen in
    # the DoxyXML. 
    c.includeCppCode('src/app_ex.cpp')
