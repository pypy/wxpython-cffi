extern "C" size_t (*PyInputStream_OnSysRead)(void*, void*, size_t);
extern "C" int (*PyInputStream_IsSeekable)(void*);
extern "C" size_t (*PyInputStream_TellI)(void*);
extern "C" size_t (*PyInputStream_SeekI)(void*, size_t, int);

// This class can wrap a Python file-like object and allow it to be used 
// as a wxInputStream.
class wxPyInputStream : public wxInputStream
{
private:
    void* m_file_handle;

public:

    wxPyInputStream(void* file_handle)
	: m_file_handle(file_handle)
    { 
	WL_ADJUST_REFCOUNT(m_file_handle, 1);
    }
    
    virtual ~wxPyInputStream()
    {
	WL_ADJUST_REFCOUNT(m_file_handle, -1);
    }

    wxPyInputStream(const wxPyInputStream& other) 
	: m_file_handle(other.m_file_handle)
    {
	WL_ADJUST_REFCOUNT(m_file_handle, 1);
    }
    
protected:

    // implement base class virtuals
    virtual size_t OnSysRead(void *buffer, size_t size)
    {
	return (*PyInputStream_OnSysRead)(m_file_handle, buffer, size);
    }

    bool IsSeekable() const 
    {
	return (*PyInputStream_IsSeekable)(m_file_handle);
    }

    wxFileOffset TellI() const 
    {
	return (*PyInputStream_TellI)(m_file_handle);
    }

    wxFileOffset SeekI(wxFileOffset pos, wxSeekMode mode = wxFromStart)
    {
	return (*PyInputStream_SeekI)(m_file_handle, pos, mode);
    }

};
