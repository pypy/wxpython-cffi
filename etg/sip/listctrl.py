def run(module):
    c = module.find('wxListCtrl')

    # Tweaks to allow passing and using a Python callable object for the sort
    # compare function. First provide a sort callback function that can call the
    # Python function.
    c.addCppCode("""\
        static int wxCALLBACK wxPyListCtrl_SortItems(wxIntPtr item1, wxIntPtr item2, wxIntPtr funcPtr) 
        {
            int retval = 0;
            PyObject* func = (PyObject*)funcPtr;
            wxPyThreadBlocker blocker;

            PyObject* args = Py_BuildValue("(ii)", item1, item2);
            PyObject* result = PyEval_CallObject(func, args);
            Py_DECREF(args);
            if (result) {
                retval = wxPyInt_AsLong(result);
                Py_DECREF(result);
            }
  
            return retval;
        }
        """)
    
    # Next, provide an alternate implementation of SortItems that will use that callback.
    sim = c.find('SortItems')
    assert isinstance(sim, etgtools.MethodDef)
    sim.find('fnSortCallBack').type = 'PyObject*'
    sim.find('data').ignore() # we will be using it to pass the python callback function
    sim.argsString = sim.argsString.replace('wxListCtrlCompare', 'PyObject*')
    sim.setCppCode("""\
        if (!PyCallable_Check(fnSortCallBack))
            return false;
        return self->SortItems((wxListCtrlCompare)wxPyListCtrl_SortItems, 
                               (wxIntPtr)fnSortCallBack);       
    """)
    


    c.addCppMethod(
        'PyObject*', 'HitTestSubItem', '(const wxPoint& point)', 
        pyArgsString="HitTestSubItem(point) -> (item, flags, subitem)",
        doc="Determines which item (if any) is at the specified point, giving details in flags.",
        body="""\
            long item, subitem;
            int flags;
            item = self->HitTest(*point, flags, &subitem);
            wxPyThreadBlocker blocker;
            PyObject* rv = PyTuple_New(3);
            PyTuple_SetItem(rv, 0, wxPyInt_FromLong(item));
            PyTuple_SetItem(rv, 1, wxPyInt_FromLong(flags));
            PyTuple_SetItem(rv, 2, wxPyInt_FromLong(subitem));
            return rv;
            """)
