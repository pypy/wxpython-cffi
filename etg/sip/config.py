def run(module):
    c = module.find('wxConfigBase')

    c.find('GetFirstGroup').ignore()
    c.find('GetNextGroup').ignore()
    c.find('GetFirstEntry').ignore()
    c.find('GetNextEntry').ignore()
    
    c.addCppCode("""\
        static PyObject* _Config_EnumerationHelper(bool flag, wxString& str, long index) {
        wxPyThreadBlocker blocker;
            PyObject* ret = PyTuple_New(3);
            if (ret) {
                PyTuple_SET_ITEM(ret, 0, PyBool_FromLong(flag));
                PyTuple_SET_ITEM(ret, 1, wx2PyString(str));
                PyTuple_SET_ITEM(ret, 2, wxPyInt_FromLong(index));
            }
            return ret;
        }
        """)

    c.addCppMethod('PyObject*', 'GetFirstGroup', '()',
        doc="""\
            GetFirstGroup() -> (more, value, index)\n            
            Allows enumerating the subgroups in a config object.  Returns a tuple
            containing a flag indicating if there are more items, the name of the
            current item, and an index to pass to GetNextGroup to fetch the next
            item.""",
        body="""\
            bool     more;
            long     index = 0;
            wxString value;
            more = self->GetFirstGroup(value, index);
            return _Config_EnumerationHelper(more, value, index);
            """)
            
    c.addCppMethod('PyObject*', 'GetNextGroup', '(long index)',
        doc="""\
            GetNextGroup(long index) -> (more, value, index)\n
            Allows enumerating the subgroups in a config object.  Returns a tuple
            containing a flag indicating if there are more items, the name of the
            current item, and an index to pass to GetNextGroup to fetch the next
            item.""",
        body="""\
            bool more;
            wxString value;
            more = self->GetNextGroup(value, index);
            return _Config_EnumerationHelper(more, value, index);
            """)
    
            
    c.addCppMethod('PyObject*', 'GetFirstEntry', '()',
        doc="""\
            GetFirstEntry() -> (more, value, index)\n
            Allows enumerating the entries in the current group in a config
            object.  Returns a tuple containing a flag indicating if there are more
            items, the name of the current item, and an index to pass to
            GetNextEntry to fetch the next item.""",
        body="""\
            bool     more;
            long     index = 0;
            wxString value;
            more = self->GetFirstEntry(value, index);
            return _Config_EnumerationHelper(more, value, index);
            """)
    
    c.addCppMethod('PyObject*', 'GetNextEntry', '(long index)',
        doc="""\
            GetNextEntry() -> (more, value, index)\n
            Allows enumerating the entries in the current group in a config
            object.  Returns a tuple containing a flag indicating if there are more
            items, the name of the current item, and an index to pass to
            GetNextEntry to fetch the next item.""",
        body="""\
            bool     more;
            wxString value;
            more = self->GetNextEntry(value, index);
            return _Config_EnumerationHelper(more, value, index);
            """)

