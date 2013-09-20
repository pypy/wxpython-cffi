def run(module):
    c = module.find('wxEvtHandler')

    c.includeCppCode('src/event_ex.cpp')
    
    # Connect and disconnect methods for wxPython. Hold a reference to the
    # event handler function in the event table, so we can fetch it later when
    # it is time to handle the event.
    c.addCppMethod(
        'void', 'Connect', '(int id, int lastId, wxEventType eventType, PyObject* func)',
        doc="Make an entry in the dynamic event table for an event binding.",
        body="""\
            if (PyCallable_Check(func)) {
                self->Connect(id, lastId, eventType,
                              (wxObjectEventFunction)(wxEventFunction)
                              &wxPyCallback::EventThunker,
                              new wxPyCallback(func));
            }
            else if (func == Py_None) {
                self->Disconnect(id, lastId, eventType,
                                 (wxObjectEventFunction)(wxEventFunction)
                                 &wxPyCallback::EventThunker);
            }
            else {
                PyErr_SetString(PyExc_TypeError, "Expected callable object or None.");
            }
        """)


    c.addCppMethod(
        'bool', 'Disconnect', '(int id, int lastId=-1, '
                               'wxEventType eventType=wxEVT_NULL, '
                               'PyObject* func=NULL)', 
        doc="Remove an event binding by removing its entry in the dynamic event table.",
        body="""\
            if (func && func != Py_None) {
                // Find the current matching binder that has this function
                // pointer and dissconnect that one.  Unfortuneatly since we
                // wrapped the PyObject function pointer in another object we
                // have to do the searching ourselves...
                wxList::compatibility_iterator node = self->GetDynamicEventTable()->GetFirst();
                while (node)
                {
                    wxDynamicEventTableEntry *entry = (wxDynamicEventTableEntry*)node->GetData();
                    if ((entry->m_id == id) &&
                        ((entry->m_lastId == lastId) || (lastId == wxID_ANY)) &&
                        ((entry->m_eventType == eventType) || (eventType == wxEVT_NULL)) &&
                        // FIXME?
                        //((entry->m_fn->IsMatching((wxObjectEventFunction)(wxEventFunction)&wxPyCallback::EventThunker))) &&
                        (entry->m_callbackUserData != NULL))
                    {
                        wxPyCallback *cb = (wxPyCallback*)entry->m_callbackUserData;
                        if (cb->m_func == func) {
                            delete cb;
                            self->GetDynamicEventTable()->Erase(node);
                            delete entry;
                            return true;
                        }                        
                    }
                    node = node->GetNext();
                }
                return false;
            }
            else {
                return self->Disconnect(id, lastId, eventType,
                                        (wxObjectEventFunction)
                                        &wxPyCallback::EventThunker);
            }
        """)

    #-----------------------------------------------------------------
    c = module.find('wxDropFilesEvent')

    # wxDropFilesEvent assumes that the C array of wxString objects will
    # continue to live as long as the event object does, and does not take
    # ownership of the array. Unfortunately the mechanism used to turn the
    # Python list into a C array will also delete it after the API call, and
    # so when wxDropFilesEvent tries to access it later the memory pointer is
    # bad. So we'll copy that array into a special holder class and give that
    # one to the API, and also assign a Python reference to it to the event
    # object, so it will get garbage collected later.
    c.find('wxDropFilesEvent.files').array = True
    c.find('wxDropFilesEvent.files').transfer = True    
    c.find('wxDropFilesEvent.noFiles').arraySize = True
    c.addHeaderCode('#include "arrayholder.h"')
    c.find('wxDropFilesEvent').setCppCode_sip("""\
        if (files) {
            wxStringCArrayHolder* holder = new wxStringCArrayHolder;
            holder->m_array = files;   
            // Make a PyObject for the holder, and transfer its ownership to self.
            PyObject* pyHolder = sipConvertFromNewType(
                    (void*)holder, sipType_wxStringCArrayHolder, (PyObject*)sipSelf);
            Py_DECREF(pyHolder);
            sipCpp = new sipwxDropFilesEvent(id,(int)noFiles, holder->m_array);            
        }
        else
            sipCpp = new sipwxDropFilesEvent(id);
        """)
    
  
        
    c.find('GetFiles').type = 'PyObject*'
    c.find('GetFiles').setCppCode("""\
        int         count   = self->GetNumberOfFiles();
        wxString*   files   = self->GetFiles();
        wxPyThreadBlocker   blocker;
        PyObject*   list    = PyList_New(count);
        if (!list) {
            PyErr_SetString(PyExc_MemoryError, "Can't allocate list of files!");
            return NULL;
        }
        for (int i=0; i<count; i++) {
            PyObject* s = wx2PyString(files[i]);
            PyList_SET_ITEM(list, i, s);
        }
        return list;    
        """)
    
