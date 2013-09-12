import etgtools

def run(module):
    c = module.find('wxColour')

    # Use a CppMethodDef_cffi here instead of a PyMethod so that the method
    # is included in the class body itself and not monkey-patched in
    c.addItem(etgtools.CppMethodDef_cffi(
        type='void', name='Get',
        argsString='()', pyArgsString='(self, includeAlpha=True)',
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
        body='',
        briefDoc="""\
        Get(includeAlpha=False) -> (r,g,b) or (r,g,b,a)\n
        Returns the RGB intensity values as a tuple, optionally the alpha value as well."""))
