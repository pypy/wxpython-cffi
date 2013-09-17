def addGetAllFormats(klass, pureVirtual=False):
    # Replace the GetAllFormats method with an implementation that returns
    # the formats as a Python list
    m = klass.findItem('GetAllFormats')
    if m:
        m.ignore()        

    pyArgs = '(dir=Get)' if klass.name == 'wxDataObject' else '(dir=DataObject.Get)'
    
    klass.addCppMethod('PyObject*', 'GetAllFormats', '(wxDataObject::Direction dir=wxDataObject::Get)',
        cppSignature='void (wxDataFormat* formats, Direction dir)',
        pyArgsString=pyArgs,
        isVirtual=True, 
        isPureVirtual=pureVirtual,
        isConst=True,
        doc="""\
            Returns a list of wx.DataFormat objects which this data object
            supports transfering in the given direction.""",
        body="""\
            size_t count = self->GetFormatCount(dir);
            wxDataFormat* formats = new wxDataFormat[count];
            self->GetAllFormats(formats, dir);
            wxPyThreadBlocker blocker;
            PyObject* list = PyList_New(count);
            for (size_t i=0; i<count; i++) {
                wxDataFormat* format = new wxDataFormat(formats[i]);
                PyObject* obj = wxPyConstructObject((void*)format, wxT("wxDataFormat"), true);
                PyList_SET_ITEM(list, i, obj); // PyList_SET_ITEM steals a reference
            }            
            delete [] formats;
            return list;
            """,
        
        # This code will be used in the function that calls a Python implementation 
        # of this method. So we need to translate between the real C++ siganture 
        # and the Python signature.
        virtualCatcherCode="""\
            // VirtualCatcherCode for wx.DataObject.GetAllFormats
            PyObject *resObj = sipCallMethod(0,sipMethod,"F",dir,sipType_wxDataObject_Direction);
            if (resObj) {
                if (!PySequence_Check(resObj)) {
                    PyErr_SetString(PyExc_TypeError, "Should return a list of wx.DataFormat objects.");
                    // or this?  sipBadCatcherResult(sipMethod);
                }
                else {
                    Py_ssize_t len = PySequence_Length(resObj);
                    Py_ssize_t idx;
                    for (idx=0; idx<len; idx+=1) {
                        PyObject* item = PySequence_GetItem(resObj, idx);
                        if (! sipCanConvertToType(item, sipType_wxDataFormat, SIP_NOT_NONE)) {
                            PyErr_SetString(PyExc_TypeError, "List of wx.DataFormat objects expected.");
                            // or this?  sipBadCatcherResult(sipMethod);
                            Py_DECREF(item);
                            break;
                        }
                        wxDataFormat* fmt;
                        int err = 0;
                        fmt = (wxDataFormat*)sipConvertToType(
                                                item, sipType_wxDataFormat, NULL, 
                                                SIP_NOT_NONE|SIP_NO_CONVERTORS, NULL, &err);
                        formats[idx] = *fmt;
                        Py_DECREF(item);
                    }
                }
            }
            if (PyErr_Occurred())
                PyErr_Print();
            Py_XDECREF(resObj);            
            """ if pureVirtual else "")

#---------------------------------------------------------------------------

def run(module):
    c = module.find('wxDataObject')

    addGetAllFormats(c, True)

    # Replace the GetDataHere method with a version that uses a smarter
    # Python buffer object instead of a stupid void pointer.
    c.find('GetDataHere').ignore()        
    c.addCppMethod('bool', 'GetDataHere', '(const wxDataFormat& format, wxPyBuffer* buf)',
        cppSignature='bool (const wxDataFormat& format, void* buf)',
        isVirtual=True, isPureVirtual=True,
        isConst=True,
        doc="Copies this data object's data in the requested format to the buffer provided.",
        body="""\
            if (!buf->checkSize(self->GetDataSize(*format)))
                return false;
            return self->GetDataHere(*format, buf->m_ptr);
            """,

        # This code will be used in the function that calls a Python implementation 
        # of this method.
        virtualCatcherCode="""\
            // Call self.GetDataSize() to find out how big the buffer should be
            PyObject* self = NULL; 
            PyObject* fmtObj = NULL;
            PyObject* sizeObj = NULL;
            PyObject* buffer = NULL;
            PyObject* resObj = NULL;
            Py_ssize_t size = 0;
            
            self = PyMethod_Self(sipMethod); // this shouldn't fail, and the reference is borrowed
            
            fmtObj = wxPyConstructObject((void*)&format, "wxDataFormat", false);
            if (!fmtObj) goto error;
            sizeObj = PyObject_CallMethod(self, "GetDataSize", "(O)", fmtObj, NULL);
            if (!sizeObj) goto error;
            size = wxPyInt_AsSsize_t(sizeObj);

            // Make a buffer that big using the pointer passed to us, and then 
            // call the Python method.
            buffer = wxPyMakeBuffer(buf, size);
            resObj = sipCallMethod(0, sipMethod, "SS", fmtObj, buffer);

            if (!resObj || sipParseResult(0,sipMethod,resObj,"b",&sipRes) < 0)
                PyErr_Print();
            
            error:
            Py_XDECREF(resObj);
            Py_XDECREF(buffer);
            Py_XDECREF(fmtObj);
            Py_XDECREF(sizeObj);
            """)
   
    # Replace the SetData method with an implementation that uses Python
    # buffer objects.
    c.find('SetData').ignore()
    c.addCppMethod('bool', 'SetData', '(const wxDataFormat& format, wxPyBuffer* buf)',
        cppSignature='bool (const wxDataFormat& format, size_t len, const void* buf)',
        isVirtual=True,
        doc="Copies data from the provided buffer to this data object for the specified format.",
        body="return self->SetData(*format, buf->m_len, buf->m_ptr);",
        
        # This code will be used in the function that calls a Python implementation 
        # of this method.
        virtualCatcherCode="""\
            PyObject* buffer = wxPyMakeBuffer((void*)buf, len);
            PyObject *resObj = sipCallMethod(0,sipMethod,"NS",
                                   new wxDataFormat(format),sipType_wxDataFormat,NULL,
                                   buffer);
            if (!resObj || sipParseResult(0,sipMethod,resObj,"b",&sipRes) < 0)
                PyErr_Print();
            Py_XDECREF(resObj);
            Py_XDECREF(buffer);
            """)

    #------------------------------------------------------------
    c = module.find('wxDataObjectSimple')

    c.addCppCtor_sip('(const wxString& formatName)', 
        body='sipCpp = new sipwxDataObjectSimple(wxDataFormat(*formatName));')
    
    # As in wxDataObject above replace GetDataHere and SetData with methods
    # that use buffer objects instead of void*, but this time we do not pass
    # a DataFormat object with it.
    c.find('GetDataHere').ignore()        
    c.addCppMethod('bool', 'GetDataHere', '(wxPyBuffer* buf)',
        cppSignature='bool (void* buf)',
        isVirtual=True,
        isConst=True,
        doc="Copies this data object's data bytes to the given buffer",
        body="""\
            if (!buf->checkSize(self->GetDataSize()))
                return false;
            return self->GetDataHere(buf->m_ptr);
            """,
        virtualCatcherCode="""\
            // Call self.GetDataSize() to find out how big the buffer should be
            PyObject* self = NULL; 
            PyObject* sizeObj = NULL;
            PyObject* buffer = NULL;
            PyObject* resObj = NULL;
            Py_ssize_t size = 0;
            
            self = PyMethod_Self(sipMethod);
            
            sizeObj = PyObject_CallMethod(self, "GetDataSize", "", NULL);
            if (!sizeObj) goto error;
            size = wxPyInt_AsSsize_t(sizeObj);

            // Make a buffer that big using the pointer passed to us, and then 
            // call the Python method.
            buffer = wxPyMakeBuffer(buf, size);
            resObj = sipCallMethod(0, sipMethod, "S", buffer);

            if (!resObj || sipParseResult(0,sipMethod,resObj,"b",&sipRes) < 0)
                PyErr_Print();
            
            error:
            Py_XDECREF(resObj);
            Py_XDECREF(buffer);
            Py_XDECREF(sizeObj);
            """)
   
    c.find('SetData').ignore()
    c.addCppMethod('bool', 'SetData', '(wxPyBuffer* buf)',
        cppSignature='bool (size_t len, const void* buf)',
        isVirtual=True,
        doc="Copies data from the provided buffer to this data object.",
        body="return self->SetData(buf->m_len, buf->m_ptr);",
        virtualCatcherCode="""\
            PyObject* buffer = wxPyMakeBuffer((void*)buf, len);
            PyObject *resObj = sipCallMethod(0,sipMethod,"S",buffer);
            if (!resObj || sipParseResult(0,sipMethod,resObj,"b",&sipRes) < 0)
                PyErr_Print();
            Py_XDECREF(resObj);
            Py_XDECREF(buffer);
            """)

    addGetAllFormats(c)
    
    #------------------------------------------------------------
    c = module.find('wxCustomDataObject')

    c.addCppCtor_sip('(const wxString& formatName)', 
        body='sipCpp = new sipwxCustomDataObject(wxDataFormat(*formatName));')

    c.find('GetData').ignore()
    c.addCppMethod('PyObject*', 'GetData', '()', isConst=True,
        doc="Returns a reference to the data buffer.",
        body="return wxPyMakeBuffer(self->GetData(), self->GetSize());")
            
    c.find('SetData').ignore()
    c.addCppMethod('bool', 'SetData', '(wxPyBuffer* buf)',
        cppSignature='bool (size_t len, const void* buf)',
        isVirtual=True,
        doc="Copies data from the provided buffer to this data object's buffer",
        body="return self->SetData(buf->m_len, buf->m_ptr);")

    #------------------------------------------------------------
    c = module.find('wxDataObjectComposite')
    addGetAllFormats(c)
    
    #------------------------------------------------------------
    c = module.find('wxTextDataObject')
    addGetAllFormats(c)

    #------------------------------------------------------------
    c = module.find('wxURLDataObject')
    addGetAllFormats(c)
