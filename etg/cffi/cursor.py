import etgtools

def run(module):
    # Add a wxBLACK manually so that it works in funciton paramter defaults
    module.addCppCode('wxCursor *wxPyHOURGLASS_CURSOR = new wxCursor;')
    module.addItem(etgtools.GlobalVarDef(
        type='wxCursor*', name='wxPyHOURGLASS_CURSOR', pyName='wxHOURGLASS_CURSOR'))


