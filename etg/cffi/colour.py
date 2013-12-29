import etgtools

def run(module):
    c = module.find('wxColour')

    '''
    m = c.find('wxColour')
    for o in m.overloads:
        if 'wxString' in o.argsString:
            o.ignored = False
            break
    m.renameOverload('wxString', '_fromString')
    '''
    c.addCppMethod(
        'wxColour*', '_fromString', '(const wxString* name)', isStatic=True,
        factory=True, body="return new wxColour(*name);")

    # Add a wxBLACK manually so that it works in funciton paramter defaults
    module.addCppCode('wxColour *wxPyBLACK = new wxColour;')
    module.addItem(etgtools.GlobalVarDef(
        type='wxColour*', name='wxPyBLACK', pyName='wxBLACK'))

    c.find('GetAsString.flags').default = 'C2S_NAME|C2S_CSS_SYNTAX'

    # Use a CppMethodDef_cffi here instead of a PyMethod so that the method
    # is included in the class body itself and not monkey-patched in
    c.addItem(etgtools.CppMethodDef_cffi(
        'Get',
        pyArgs=etgtools.ArgsString('(WL_Self self, bool includeAlpha=True)'),
        pyBody="""\
        if self.IsOk():
            red =   self.Red();
            green = self.Green()
            blue =  self.Blue()
            alpha = self.Alpha()
        else:
            red = -1
            green = -1
            blue = -1
            alpha = _core.ALPHA_OPAQUE;

        if includeAlpha:
            return (red, green, blue, alpha)
        else:
            return (red, green, blue)
        """,
        briefDoc="""\
        Get(includeAlpha=False) -> (r,g,b) or (r,g,b,a)\n
        Returns the RGB intensity values as a tuple, optionally the alpha value as well."""))
