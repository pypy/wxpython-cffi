#include <wx/wx.h>
#include <wx/sharedptr.h>

extern "C" { void (*wxPyEventDict_deleted)(void*); }

class wxPyEventDict;
typedef wxSharedPtr<wxPyEventDict> wxPyEventDictPtr;

class wxPyEventDict
{
public:
    void *m_dict;

    wxPyEventDict(void *ptr)
     : m_dict(ptr) { }

    ~wxPyEventDict()
    {
        wxPyEventDict_deleted(m_dict);
    }
};


class wxPyEvent : wxEvent
{
    DECLARE_DYNAMIC_CLASS(wxPyEvent)

public:
    wxPyEventDictPtr m_ptr;
    wxPyEvent(int id=0, wxEventType eventType = wxEVT_NULL, wxPyEventDict *ptr=NULL)
        : wxEvent(id, eventType), m_ptr(new wxPyEventDict(ptr)) {}

    virtual wxEvent* Clone() const { return new wxPyEvent(*this); }
};

IMPLEMENT_DYNAMIC_CLASS(wxPyEvent, wxEvent);

class wxPyCommandEvent : wxCommandEvent
{
    DECLARE_DYNAMIC_CLASS(wxPyCommandEvent)

public:
    wxSharedPtr<wxPyEventDict> m_ptr;
    wxPyCommandEvent(int id=0, wxEventType eventType = wxEVT_NULL, wxPyEventDict *ptr=NULL)
        : wxCommandEvent(id, eventType), m_ptr(new wxPyEventDict(ptr)) {}

    virtual wxCommandEvent* Clone() const  { return new wxPyCommandEvent(*this); }
};

IMPLEMENT_DYNAMIC_CLASS(wxPyCommandEvent, wxCommandEvent);
