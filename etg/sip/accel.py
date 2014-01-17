def run(module):
    c = module.find('wxAcceleratorTable')

    # Replace the implementation of the AcceleratorTable ctor so it can
    # accept a Python sequence of tuples or AcceleratorEntry objects like
    # Classic does. Using the arraySize and array annotations does let us
    # pass a list of entries, but they have to already be AccelertorEntry
    # obejcts. We want to allow Items in the list to be either
    # wx.AcceleratorEntry items or a 3-tuple containing the values to pass to
    # the wx.AcceleratorEntry ctor.

    # and add the code for the new constructor
    c.addCppCtor(
        briefDoc="TODO",
        argsString='(PyObject* entries)', 
        body="""\
    const char* errmsg = "Expected a sequence of 3-tuples or wx.AcceleratorEntry objects.";
    if (!PySequence_Check(entries)) {
        PyErr_SetString(PyExc_TypeError, errmsg);
        return NULL;
    }
    int count = PySequence_Size(entries);
    wxAcceleratorEntry* tmpEntries = new wxAcceleratorEntry[count];
    if (! tmpEntries) {
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate temporary array");
        return NULL;
    }
    int idx;
    for (idx=0; idx<count; idx++) {
        PyObject* obj = PySequence_ITEM(entries, idx);
        if (sipCanConvertToType(obj, sipType_wxAcceleratorEntry, SIP_NO_CONVERTORS)) {
            int err = 0;
            wxAcceleratorEntry* entryPtr = reinterpret_cast<wxAcceleratorEntry*>(
                sipConvertToType(obj, sipType_wxAcceleratorEntry, NULL, 0, 0, &err));
            tmpEntries[idx] = *entryPtr;
        }
        else if (PySequence_Check(obj) && PySequence_Size(obj) == 3) {
            PyObject* o1 = PySequence_ITEM(obj, 0);
            PyObject* o2 = PySequence_ITEM(obj, 1);
            PyObject* o3 = PySequence_ITEM(obj, 2);
            tmpEntries[idx].Set(wxPyInt_AsLong(o1), wxPyInt_AsLong(o2), wxPyInt_AsLong(o3));
            Py_DECREF(o1);
            Py_DECREF(o2);
            Py_DECREF(o3);            
        }
        else {
            PyErr_SetString(PyExc_TypeError, errmsg);
            return NULL;
        }
        Py_DECREF(obj);
    }
    
    wxAcceleratorTable* table = new wxAcceleratorTable(count, tmpEntries);
    delete tmpEntries;
    return table;
    """)

