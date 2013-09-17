import etgtools

def run(module):
    c = module.find('wxPen')

    # SetDashes does not take ownership of the array passed to it, yet that
    # array must be kept alive as long as the pen lives. The code that the sip
    # backend uses (creating an array holder object) doesn't actually work (the
    # array is never deleted because the PyObject is owned by C++.) For a
    # temporary solution, just leak the array for the time being.
    m = c.find('SetDashes')
    # ignore the existing parameters
    m.find('n').ignore()
    m.find('dash').ignore()
    # add a new one
    m.items.append(etgtools.ParamDef(type='const wxArrayInt&', name='dashes'))
    m.setCppCode("""\
        size_t len = dashes->GetCount();
        wxDash *array = new wxDash[len];
        for (int idx=0; idx<len; idx+=1)
            array[idx] = (*dashes)[idx];
        self->SetDashes(len, array);
        """)

