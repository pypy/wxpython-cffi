typedef WL_RefCountedPyObjBase<wxObject> wxPyCallback;


extern "C" void (*wxPyCallback_event_thunk)(void*, void*);

class wxPyEventThunker : public wxEvtHandler
{
public:
    void EventThunk(wxEvent &event)
    {
        wxPyCallback *cb = (wxPyCallback*)event.GetEventUserData();
        void *callback = cb->get_handle();

        wxPyCallback_event_thunk(callback, &event);
    }
};


