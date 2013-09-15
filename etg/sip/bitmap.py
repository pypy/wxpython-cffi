def run(module):
    c = module.find('wxBitmap')

    c.addCppCtor('(PyObject* listOfBytes)',
        doc="Construct a Bitmap from a list of strings formatted as XPM data.",
        body="""\
            wxPyThreadBlocker blocker;
            char**    cArray = NULL;
            int       count;
            char      errMsg[] = "Expected a list of bytes objects.";
            
            if (!PyList_Check(listOfBytes)) {
                PyErr_SetString(PyExc_TypeError, errMsg);
                return NULL;
            }
            count = PyList_Size(listOfBytes);
            cArray = new char*[count];

            for(int x=0; x<count; x++) {
                PyObject* item = PyList_GET_ITEM(listOfBytes, x);
                if (!PyBytes_Check(item)) {
                    PyErr_SetString(PyExc_TypeError, errMsg);
                    delete [] cArray;
                    return NULL;
                }
                cArray[x] = PyBytes_AsString(item);
            }
            wxBitmap* bmp = new wxBitmap(cArray);
            delete [] cArray;
            return bmp;
            """)

