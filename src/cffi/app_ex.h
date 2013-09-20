class wxPyApp : public wxApp
{
    DECLARE_ABSTRACT_CLASS(wxPyApp)

public:
    wxPyApp() : wxApp() {
        m_assertMode = wxAPP_ASSERT_EXCEPTION;
        m_startupComplete = false;
        //m_callFilterEvent = false;
        ms_appInstance = this;
    }

    ~wxPyApp() {
        ms_appInstance = NULL;
        wxApp::SetInstance(NULL);
    }


#ifndef __WXMAC__
    virtual void MacNewFile() {}
    virtual void MacOpenFile(const wxString &) {}
    virtual void MacOpenFiles(const wxArrayString& fileNames) {}
    virtual void MacOpenURL(const wxString &) {}
    virtual void MacPrintFile(const wxString &) {}
    virtual void MacReopenApp() {}
#endif

#ifdef __WXMAC__
    static long GetMacAboutMenuItemId()               { return s_macAboutMenuItemId; }
    static long GetMacPreferencesMenuItemId()         { return s_macPreferencesMenuItemId; }
    static long GetMacExitMenuItemId()                { return s_macExitMenuItemId; }
    static wxString GetMacHelpMenuTitleName()         { return s_macHelpMenuTitleName; }
    static void SetMacAboutMenuItemId(long val)       { s_macAboutMenuItemId = val; }
    static void SetMacPreferencesMenuItemId(long val) { s_macPreferencesMenuItemId = val; }
    static void SetMacExitMenuItemId(long val)        { s_macExitMenuItemId = val; }
    static void SetMacHelpMenuTitleName(const wxString& val) { s_macHelpMenuTitleName = val; }
#else
    static long GetMacAboutMenuItemId()               { return 0; }
    static long GetMacPreferencesMenuItemId()         { return 0; }
    static long GetMacExitMenuItemId()                { return 0; }
    static wxString GetMacHelpMenuTitleName()         { return wxEmptyString; }
    static void SetMacAboutMenuItemId(long)           { }
    static void SetMacPreferencesMenuItemId(long)     { }
    static void SetMacExitMenuItemId(long)            { }
    static void SetMacHelpMenuTitleName(const wxString&) { }
#endif

    wxAppAssertMode  GetAssertMode() { return m_assertMode; }
    void SetAssertMode(wxAppAssertMode mode) {
        m_assertMode = mode;
        if (mode & wxAPP_ASSERT_SUPPRESS)
            wxDisableAsserts();
        else
            wxSetDefaultAssertHandler();
    }

    virtual void OnAssertFailure(const wxChar *file,
                                 int line,
                                 const wxChar *func,
                                 const wxChar *cond,
                                 const wxChar *msg);


    // Implementing OnInit is optional for wxPython apps
    virtual bool OnInit()     { return true; }
    virtual void OnPreInit()  { }

    void _BootstrapApp(int argc, wchar_t **argv);
    virtual int MainLoop();

    static bool IsDisplayAvailable();

    // implementation only
    void SetStartupComplete(bool val) { m_startupComplete = val; }
    static wxPyApp* ms_appInstance;

private:
    wxAppAssertMode m_assertMode;
    bool m_startupComplete;
    //bool m_callFilterEvent;
};
