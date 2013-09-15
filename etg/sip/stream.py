def run(module):
    c = module.find('wxInputStream')

    # Include a C++ class that can wrap a Python file-like object so it can
    # be used as a wxInputStream
    c.includeCppCode('src/stream_input.cpp')
    
    c.addCppCode("""\
        // helper used by the read and readline methods to make a PyObject
        static PyObject* _makeReadBufObj(wxInputStream* self, wxMemoryBuffer& buf) {
            PyObject* obj = NULL;

            wxPyThreadBlocker blocker;
            wxStreamError err = self->GetLastError();  // error check
            if (err != wxSTREAM_NO_ERROR && err != wxSTREAM_EOF) {
                PyErr_SetString(PyExc_IOError,"IOError in wxInputStream");
            }
            else {
                // Return the data as a string object.  TODO: Py3
                obj = PyBytes_FromStringAndSize(buf, buf.GetDataLen());
            }
            return obj;
        }
        """)
            

    c.addCppMethod('PyObject*', 'read', '()', """\
        wxMemoryBuffer buf;
        const size_t BUFSIZE = 1024;

        // read while bytes are available on the stream
        while ( self->CanRead() ) {
            self->Read(buf.GetAppendBuf(BUFSIZE), BUFSIZE);
            buf.UngetAppendBuf(self->LastRead());
        }
        return _makeReadBufObj(self, buf);
        """)
    
    c.addCppMethod('PyObject*', 'read', '(size_t size)', """\
        wxMemoryBuffer buf;

        // Read only size number of characters
        self->Read(buf.GetWriteBuf(size), size);
        buf.UngetWriteBuf(self->LastRead());
        return _makeReadBufObj(self, buf);
        """)

    c.addCppMethod('PyObject*', 'readline', '()', """\
        wxMemoryBuffer buf;
        char ch = 0;

        // read until \\n 
        while ((ch != '\\n') && (self->CanRead())) {
            ch = self->GetC();
            buf.AppendByte(ch);
        }
        return _makeReadBufObj(self, buf);
        """)

    c.addCppMethod('PyObject*', 'readline', '(size_t size)', """\
        wxMemoryBuffer buf;
        int i;
        char ch;

        // read until \\n or byte limit reached
        for (i=ch=0; (ch != '\\n') && (self->CanRead()) && (i < size); i++) {
            ch = self->GetC();
            buf.AppendByte(ch);
        }
        return _makeReadBufObj(self, buf);
        """)


    c.addCppCode("""\
        PyObject* _wxInputStream_readline(wxInputStream* self);
        
        // This does the real work of the readlines methods
        static PyObject* _readlinesHelper(wxInputStream* self, 
                                          bool useSizeHint=false, size_t sizehint=0) {
            PyObject* pylist;
    
            // init list
            wxPyBlock_t blocked = wxPyBeginBlockThreads();
            pylist = PyList_New(0);
            wxPyEndBlockThreads(blocked);
    
            if (!pylist) {
                wxPyBlock_t blocked = wxPyBeginBlockThreads();
                PyErr_NoMemory();
                wxPyEndBlockThreads(blocked);
                return NULL;
            }
    
            // read sizehint bytes or until EOF
            size_t i;
            for (i=0; (self->CanRead()) && (useSizeHint || (i < sizehint));) {
                PyObject* s = _wxInputStream_readline(self);
                if (s == NULL) {
                    wxPyBlock_t blocked = wxPyBeginBlockThreads();
                    Py_DECREF(pylist);
                    wxPyEndBlockThreads(blocked);
                    return NULL;
                }
                wxPyBlock_t blocked = wxPyBeginBlockThreads();
                PyList_Append(pylist, s);
                i += PyBytes_Size(s);
                wxPyEndBlockThreads(blocked);
            }
    
            // error check
            wxStreamError err = self->GetLastError();
            if (err != wxSTREAM_NO_ERROR && err != wxSTREAM_EOF) {
                wxPyBlock_t blocked = wxPyBeginBlockThreads();
                Py_DECREF(pylist);
                PyErr_SetString(PyExc_IOError,"IOError in wxInputStream");
                wxPyEndBlockThreads(blocked);
                return NULL;
            }    
            return pylist;        
        }
        """)
    
    c.addCppMethod('PyObject*', 'readlines', '()', """\
        return _readlinesHelper(self);
        """)
    c.addCppMethod('PyObject*', 'readlines', '(size_t sizehint)', """\
        return _readlinesHelper(self, true, sizehint);
        """)
    

    #-----------------------------------------------------------------
    c = module.find('wxOutputStream')

    # Include a C++ class that can wrap a Python file-like object so it can
    # be used as a wxOutputStream
    c.includeCppCode('src/stream_output.cpp')

    c.addCppMethod('void', 'write', '(PyObject* data)', """\
        // We use only strings for the streams, not unicode
        PyObject* str = PyObject_Bytes(data);
        if (! str) {
            PyErr_SetString(PyExc_TypeError, "Unable to convert to string");
            return;
        }
        self->Write(PyBytes_AS_STRING(str), PyBytes_GET_SIZE(str));
        Py_DECREF(str);
        """)
    
