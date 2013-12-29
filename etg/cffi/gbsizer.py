import etgtools

def run(module):
    c = module.find('wxGBPosition')
    c.addItem(etgtools.CppMethodDef_cffi(
        'Get', 
        pyArgs=etgtools.ArgsString('(WL_Self self)'),
        pyBody="return (self.GetRow(), self.GetCol())",
        briefDoc="Return the row and col properties as a tuple."))

    c = module.find('wxGBSpan')
    c.addItem(etgtools.CppMethodDef_cffi(
        'Get',
        pyArgs=etgtools.ArgsString('WL_Self self)'),
        pyBody="return (self.GetRowspan(), self.GetColspan())",
        briefDoc="Return the rowspan and colspan properties as a tuple."))
