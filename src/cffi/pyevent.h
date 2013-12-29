#ifndef INCGRD_PYEVENT_H
#define INCGRD_PYEVENT_H

struct EmptyBase { };
typedef WL_RefCountedPyObjBase<EmptyBase> wxPyEventDictRef;

class wxPyEvent : public wxEvent
{
    DECLARE_DYNAMIC_CLASS(wxPyEvent)

public:
    wxPyEvent(int id=0, wxEventType eventType = wxEVT_NULL, void *handle=NULL)
        : wxEvent(id, eventType), m_dict_ref(handle) {}

    virtual wxEvent* Clone() const { return new wxPyEvent(*this); }

    wxPyEventDictRef m_dict_ref;
};

class wxPyCommandEvent : public wxCommandEvent
{
    DECLARE_DYNAMIC_CLASS(wxPyCommandEvent)

public:
    wxPyCommandEvent(int id=0, wxEventType eventType = wxEVT_NULL, void *handle=NULL)
        : wxCommandEvent(id, eventType), m_dict_ref(handle) {}

    virtual wxEvent* Clone() const  { return new wxPyCommandEvent(*this); }

    wxPyEventDictRef m_dict_ref;
};
#endif
