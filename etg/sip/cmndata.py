def run(module):
    c = module.find('wxPrintData')

    # TODO: These two methods should use something other than a PyString for
    # holding the data...
    c.addCppMethod('PyObject*', 'GetPrivData', '()', """\
        PyObject* data;
        wxPyThreadBlocker blocker;
        data = PyBytes_FromStringAndSize(self->GetPrivData(),
                                         self->GetPrivDataLen());
        return data;    
        """)
    
    c.addCppMethod('void', 'SetPrivData', '(PyObject* data)', """\
        wxPyThreadBlocker blocker;
        if (! PyBytes_Check(data)) {
            wxPyErr_SetString(PyExc_TypeError, "Expected string object");
            return;
        }

        self->SetPrivData(PyBytes_AS_STRING(data), PyBytes_GET_SIZE(data));
        """)
    
