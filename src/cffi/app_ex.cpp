
#ifdef __WXGTK__
#include <gdk/gdkx.h>
#include <gtk/gtk.h>
#include <wx/gtk/private/win_gtk.h>
#endif

#ifdef __WXMAC__
#include <wx/osx/private.h>
#endif

#ifdef __WXMSW__
#include <wx/msw/private.h>
#include <wx/msw/winundef.h>
#include <wx/msw/msvcrt.h>
#endif


#ifdef __WXMSW__             // If building for Windows...

//----------------------------------------------------------------------
// This gets run when the DLL is loaded.  We just need to save the
// instance handle.
//----------------------------------------------------------------------

extern "C"
BOOL WINAPI DllMain(
    HINSTANCE   hinstDLL,    // handle to DLL module
    DWORD       fdwReason,   // reason for calling function
    LPVOID      lpvReserved  // reserved
   )
{
    // If wxPython is embedded in another wxWidgets app then
    // the instance has already been set.
    if (! wxGetInstance())
        wxSetInstance(hinstDLL);

    return TRUE;
}
#endif  // __WXMSW__

//----------------------------------------------------------------------
// Classes for implementing the wxp main application shell.
//----------------------------------------------------------------------


IMPLEMENT_ABSTRACT_CLASS(wxPyApp, wxApp);

wxPyApp* wxPyApp::ms_appInstance = NULL;

void wxPyApp::OnAssertFailure(const wxChar *file,
                              int line,
                              const wxChar *func,
                              const wxChar *cond,
                              const wxChar *msg)
{
    // ignore it?
    if (m_assertMode & wxAPP_ASSERT_SUPPRESS)
        return;

    // turn it into a Python exception?
    if (m_assertMode & wxAPP_ASSERT_EXCEPTION) {
        wxString buf;
        buf.Alloc(4096);
        buf.Printf(wxT("C++ assertion \"%s\" failed at %s(%d)"), cond, file, line);
        if ( func && *func )
            buf << wxT(" in ") << func << wxT("()");
        if (msg != NULL)
            buf << wxT(": ") << msg;

        wxPyErr_SetString(wxAssertionError, buf.c_str());

        // Now when control returns to whatever API wrapper was called from
        // Python it should detect that an exception is set and will return
        // NULL, signalling the exception to Python.
    }

    // Send it to the normal log destination, but only if
    // not _DIALOG because it will call this too
    if ( (m_assertMode & wxAPP_ASSERT_LOG) && !(m_assertMode & wxAPP_ASSERT_DIALOG)) {
        wxString buf;
        buf.Alloc(4096);
        buf.Printf(wxT("%s(%d): assert \"%s\" failed"),
                   file, line, cond);
        if ( func && *func )
            buf << wxT(" in ") << func << wxT("()");
        if (msg != NULL)
            buf << wxT(": ") << msg;
        wxLogDebug(buf);
    }

    // do the normal wx assert dialog?
    if (m_assertMode & wxAPP_ASSERT_DIALOG)
        wxApp::OnAssertFailure(file, line, func, cond, msg);
}


void wxPyApp::_BootstrapApp(int argc, wchar_t **argv)
{
    static      bool haveInitialized = false;
    bool        result;

    // Only initialize wxWidgets once
    if (! haveInitialized) {

        // Initialize wxWidgets
#ifdef __WXOSX__
        wxMacAutoreleasePool autoreleasePool;
#endif
        result = wxEntryStart(argc, argv);
        // wxApp takes ownership of the argv array, don't delete it here

        if (! result) 
        {
            wxPyThreadBlocker blocker;
            PyErr_SetString(PyExc_SystemError,
                              "wxEntryStart failed, unable to initialize wxWidgets!"
#ifdef __WXGTK__
                              "  (Is DISPLAY set properly?)"
#endif
                );
            goto error;
        }
        haveInitialized = true;
    }
    else {
        // wxEntryStart isn't being called, so free argv
        for(int i = 0; i < argc; i++)
            free(argv[i]);
        free(argv);
        this->argc = 0;
    }

    // It's now ok to generate exceptions for assertion errors.
    SetStartupComplete(true);

    // Call the Python wxApp's OnPreInit and OnInit functions if they exist
    OnPreInit();
    result = OnInit();

    if (! result) {
        wxPyErr_SetString(PyExc_SystemExit, "OnInit returned false, exiting...");
    }
error:
    return;
}


int wxPyApp::MainLoop()
{
    int retval = 0;

    {
#ifdef __WXOSX__
        wxMacAutoreleasePool autoreleasePool;
#endif
        DeletePendingObjects();
    }
    bool initialized = wxTopLevelWindows.GetCount() != 0;
    if (initialized) {
        if ( m_exitOnFrameDelete == Later ) {
            m_exitOnFrameDelete = Yes;
        }

        retval = wxApp::MainLoop();
        OnExit();
    }
    return retval;
}


// Function to test if the Display (or whatever is the platform equivallent)
// can be connected to.
bool wxPyApp::IsDisplayAvailable()
{
#ifdef __WXGTK__
    Display* display;
    display = XOpenDisplay(NULL);
    if (display == NULL)
        return false;
    XCloseDisplay(display);
    return true;
#endif

#ifdef __WXMAC__
    // This is adapted from Python's Mac/Modules/MacOS.c in the
    // MacOS_WMAvailable function.
    bool rv;
    ProcessSerialNumber psn = { 0, kCurrentProcess };

    /*
    ** This is a fairly innocuous call to make if we don't have a window
    ** manager, or if we have no permission to talk to it. It will print
    ** a message on stderr, but at least it won't abort the process.
    ** It appears the function caches the result itself, and it's cheap, so
    ** no need for us to cache.
    */
#ifdef kCGNullDirectDisplay
    /* On 10.1 CGMainDisplayID() isn't available, and
    ** kCGNullDirectDisplay isn't defined.
    */
    if (CGMainDisplayID() == 0) {
        rv = false;
    } else 
#endif
    {
        TransformProcessType(&psn, kProcessTransformToForegroundApplication);
        // Also foreground the application on the first call as a side-effect.
        if (SetFrontProcess(&psn) < 0) {
        //if (TransformProcessType(&psn, kProcessTransformToForegroundApplication) < 0
        //    || SetFrontProcess(&psn) < 0) {
            rv = false;
        } else {
            rv = true;
        }
    }
    return rv;
#endif

#ifdef __WXMSW__
    // TODO...
    return true;
#endif
}



wxPyApp* wxGetApp()
{
    return wxPyApp::ms_appInstance;
}
