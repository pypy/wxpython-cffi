import etgtools

def run(module):
    c = module.find('wxEvtHandler')

    c.includeCppCode('src/cffi/event_ex.cpp')

    module.addCdef_cffi("void (*wxPyCallback_event_thunk)(void*, void*);")

    # Connect and disconnect methods for wxPython. Hold a reference to the
    # event handler function in the event table, so we can fetch it later when
    # it is time to handle the event.
    c.addItem(etgtools.CppMethodDef_cffi(
        'void', 'Connect',
        '(void *self_, int id, int lastId, int eventType, void* func)',
        '(self, id, lastId, eventType, func)',
        doc="Make an entry in the dynamic event table for an event binding.",
        body="""\
            wxEvtHandler *self = (wxEvtHandler *)self_;
            if (func)
                self->Connect(id, lastId, eventType,
                              (wxObjectEventFunction)(wxEventFunction)
                              &wxPyEventThunker::EventThunk,
                              new wxPyCallback(func));
            else
                self->Disconnect(id, lastId, eventType,
                                 (wxObjectEventFunction)(wxEventFunction)
                                 &wxPyEventThunker::EventThunk);
        """,
        pyBody="""\
            wrapper_lib.check_args_types(numbers.Number, id, "id",
                                         numbers.Number, lastId, "lastId",
                                         numbers.Number, eventType, "eventType")
            if func is None:
                call(wrapper_lib.get_ptr(self), int(id), int(lastId),
                     int(eventType), ffi.NULL)
                return

            if not callable(func):
                raise TypeError("argument 'func' got unexpected type '%s'" %
                                type(func))
            with wrapper_lib.get_refcounted_handle(func) as handle:
                call(wrapper_lib.get_ptr(self), int(id), int(lastId),
                     int(eventType), handle)
        """))

    c.addItem(etgtools.CppMethodDef_cffi(
        'int', 'Disconnect',
        '(void *self_, int id, int lastId, int eventType, void* func)', 
        '(self, id, lastId=-1, eventType=wrapper_lib.LD("wxEVT_NULL"), func=None)',
        doc="Remove an event binding by removing its entry in the dynamic event table.",
        body="""\
            wxEvtHandler *self = (wxEvtHandler *)self_;
            if (func) {
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
                        if (cb->get_handle() == func) {
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
                                        &wxPyEventThunker::EventThunk);
            }
        """,
        pyBody="""\
            wrapper_lib.check_args_types(numbers.Number, id, "id",
                                         numbers.Number, lastId, "lastId",
                                         numbers.Number, eventType, "eventType")
            if func is None:
                return bool(call(wrapper_lib.get_ptr(self), int(id),
                                 int(lastId), int(eventType), ffi.NULL))

            # Although the function we're calling won't be holding a reference,
            # it does need the same handle that was passed to Connect
            with wrapper_lib.get_refcounted_handle(func) as handle:
                return bool(call(wrapper_lib.get_ptr(self), int(id),
                                 int(lastId), int(eventType), handle))
        """))

    # Add the following code to the class body to initialize the callback
    c.pyCode_cffi = """\
    @ffi.callback('void(*)(void*, void*)')
    def _eventThunk(callback_id, event_ptr):
        event = wrapper_lib.obj_from_ptr(event_ptr, Event)
        callback = ffi.from_handle(callback_id)
        callback(event)
    clib.wxPyCallback_event_thunk = _eventThunk
    """


    #-----------------------------------------------------------------
    c = module.find('wxDropFilesEvent')

    # wxDropFilesEvent assumes that the C array of wxString objects will
    # continue to live as long as the event object does, and does not take
    # ownership of the array. The code that the sip backend uses (creating an
    # array holder object) doesn't actually work (the array is never deleted
    # because the PyObject is owned by C++.) For a temporary solution, just
    # leak the array for the time being. (Note that combining array and
    # transfer causes the array to not be automatically deleted.)
    c.find('wxDropFilesEvent.files').array = True
    c.find('wxDropFilesEvent.files').transfer = True    
    c.find('wxDropFilesEvent.noFiles').arraySize = True

    m = c.find('GetFiles')
    m.ignore()
    c.addItem(etgtools.CppMethodDef_cffi(
        'wchar_t **', 'GetFiles', '(void *self)', '(self)',
        briefDoc=m.briefDoc,
        body="""\
        wxDropFilesEvent *e = (wxDropFilesEvent *)self;
        wxString *files = e->GetFiles();
        int count = e->GetNumberOfFiles();

        wchar_t **cdata = (wchar_t **)malloc(sizeof(wchar_t*) * count);
        for(int i = 0; i < count; i++)
        {
            cdata[i] = (wchar_t*)malloc(sizeof(wchar_t) * (files[i].size() + 1));
            wxStrcpy(cdata[i], files[i].wc_str());
        }

        return cdata;
        """,
        pyBody="""\
        cdata = call(wrapper_lib.get_ptr(self))

        files = []
        for i in range(self.GetNumberOfFiles()):
            files.append(ffi.string(cdata[i]))
            clib.free(cdata[i])

        clib.free(cdata)
        return files
        """))
