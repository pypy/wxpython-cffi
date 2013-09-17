import etgtools

def run(module):
    c = module.find('wxPen')

    # SetDashes does not take ownership of the array passed to it, yet that
    # array must be kept alive as long as the pen lives, so we'll create an
    # array holder object that will be associated with the pen, and that will
    # delete the dashes array when it is deleted.
    #c.find('SetDashes').ignore()
    c.addHeaderCode('#include "arrayholder.h"')
    m = c.find('SetDashes')
    # ignore the existing parameters
    m.find('n').ignore()
    m.find('dash').ignore()
    # add a new one
    m.items.append(etgtools.ParamDef(type='const wxArrayInt&', name='dashes'))
    m.setCppCode_sip("""\
        size_t len = dashes->GetCount();
        wxDashCArrayHolder* holder = new wxDashCArrayHolder;
        holder->m_array = new wxDash[len];
        for (int idx=0; idx<len; idx+=1) {
            holder->m_array[idx] = (*dashes)[idx];
        }
        // Make a PyObject for the holder, and transfer its ownership to self.
        PyObject* pyHolder = sipConvertFromNewType(
                (void*)holder, sipType_wxDashCArrayHolder, (PyObject*)sipSelf);
        Py_DECREF(pyHolder);
        sipCpp->SetDashes(len, holder->m_array);
        """)

