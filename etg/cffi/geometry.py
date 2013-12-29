import etgtools

def run(module):
    c = module.find('wxPoint2DDouble')
    c.addItem(etgtools.CppMethodDef_cffi(
        'Get', 
        pyArgs=etgtools.ArgsString('(WL_Self self)'),
        pyBody="return (self.x, self.y)",
        briefDoc="""\
        Get() -> (x,y)\n
        Return the x and y properties as a tuple."""))

    c = module.find('wxRect2DDouble')
    c.addItem(etgtools.CppMethodDef_cffi(
        'Get', 
        pyArgs=etgtools.ArgsString('(WL_Self self)'),
        pyBody="return (self.x, self.y, self.width, self.height)",
        briefDoc="""\
        Get() -> (x, y, width, height)\n
        Return the rectangle's properties as a tuple."""))
