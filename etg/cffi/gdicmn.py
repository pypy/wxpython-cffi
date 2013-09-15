import etgtools

def run(module):
    c = module.findItem('wxPoint')
    c.addItem(etgtools.CppMethodDef_cffi(
        'void', 'Get', '()', pyArgsString='(self)',
        pyBody="return (self.x, self.y)"))

    c = module.findItem('wxSize')
    c.addItem(etgtools.CppMethodDef_cffi(
        'void', 'Get', '()', pyArgsString='(self)',
        pyBody="return (self.x, self.y)"))

    c = module.findItem('wxRect')
    c.addItem(etgtools.CppMethodDef_cffi(
        'void', 'Get', '()', pyArgsString='(self)',
        pyBody="return (self.x, self.y, self.height, self.width)"))

    c = module.findItem('wxRealPoint')
    c.addItem(etgtools.CppMethodDef_cffi(
        'void', 'Get', '()', pyArgsString='(self)',
        pyBody="return (self.x, self.y)"))
