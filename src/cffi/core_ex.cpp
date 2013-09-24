
#ifdef __WXMSW__             // If building for Windows...

#include <wx/msw/private.h>
#include <wx/msw/winundef.h>
#include <wx/msw/msvcrt.h>

//----------------------------------------------------------------------
// Use an ActivationContext to ensure that the new (themed) version of
// the comctl32 DLL is loaded.
//----------------------------------------------------------------------

// Note that the use of the ISOLATION_AWARE_ENABLED define replaces the
// activation context APIs with wrappers that dynamically load the API
// pointers from the kernel32 DLL so we don't have to do that ourselves.
// Using ISOLATION_AWARE_ENABLED also causes the manifest resource to be put
// in slot #2 as expected for DLLs. (See wx/msw/wx.rc)

#ifdef ISOLATION_AWARE_ENABLED

static ULONG_PTR wxPySetActivationContext()
{

    OSVERSIONINFO info;
    wxZeroMemory(info);
    info.dwOSVersionInfoSize = sizeof(OSVERSIONINFO); 
    GetVersionEx(&info);
    if (info.dwMajorVersion < 5)
        return 0;
    
    ULONG_PTR cookie = 0;
    HANDLE h;
    ACTCTX actctx;
    TCHAR modulename[MAX_PATH];

    GetModuleFileName(wxGetInstance(), modulename, MAX_PATH);
    wxZeroMemory(actctx);
    actctx.cbSize = sizeof(actctx);
    actctx.lpSource = modulename;
    actctx.lpResourceName = MAKEINTRESOURCE(2);
    actctx.hModule = wxGetInstance();
    actctx.dwFlags = ACTCTX_FLAG_HMODULE_VALID | ACTCTX_FLAG_RESOURCE_NAME_VALID;
    
    h = CreateActCtx(&actctx);
    if (h == INVALID_HANDLE_VALUE) {
        wxLogLastError(wxT("CreateActCtx"));
        return 0;
    }

    if (! ActivateActCtx(h, &cookie))
        wxLogLastError(wxT("ActivateActCtx"));
    
    return cookie;
}

static void wxPyClearActivationContext(ULONG_PTR cookie)
{
    if (! DeactivateActCtx(0, cookie))
        wxLogLastError(wxT("DeactivateActCtx"));
}

#endif  // ISOLATION_AWARE_ENABLED

#endif // __WXMSW__

void wxPyPreInit()
{
#ifdef ISOLATION_AWARE_ENABLED
    wxPySetActivationContext();
#endif
//#ifdef __WXMSW__
////     wxCrtSetDbgFlag(_CRTDBG_LEAK_CHECK_DF
////                     | _CRTDBG_CHECK_ALWAYS_DF
////                     | _CRTDBG_DELAY_FREE_MEM_DF
////         );
//#endif
//
//#ifdef WXP_WITH_THREAD
//#if wxPyUSE_GIL_STATE
//    PyEval_InitThreads();
//#else
//    PyEval_InitThreads();
//    wxPyTStates = new wxPyThreadStateArray;
//    wxPyTMutex = new wxMutex;
//
//    // Save the current (main) thread state in our array
//    PyThreadState* tstate = wxPyBeginAllowThreads();
//    wxPyEndAllowThreads(tstate);
//#endif
//#endif

    // Ensure that the build options in the DLL (or whatever) match this build
    wxApp::CheckBuildOptions(WX_BUILD_OPTIONS_SIGNATURE, "wxPython");
}

void _wxPyCleanup()
{
    wxEntryCleanup();
}

#ifdef __WXGTK__
#define wxPyPort "__WXGTK__"
#define wxPyPortName "wxGTK"
#endif
#ifdef __WXMSW__
#define wxPyPort "__WXMSW__"
#define wxPyPortName "wxMSW"
#endif
#ifdef __WXMAC__
#define wxPyPort "__WXMAC__"
#define wxPyPortName "wxMac"
#endif
#define wxPyPlatform wxPyPort

const char *wxPyPlatformInfo =
#if wxUSE_UNICODE
    "unicode, "
#if wxUSE_UNICODE_WCHAR
    "unicode-wchar, "
#else
    "unicode-utf8, "
#endif
#else
    "ansi, "
#endif

#ifdef __WXOSX__
    "wxOSX, "
#endif
#ifdef __WXOSX_CARBON__
    "wxOSX-carbon, "
#endif
#ifdef __WXOSX_COCOA__
    "wxOSX-cocoa, "
#endif
#ifdef __WXGTK__
#ifdef __WXGTK20__
    "gtk2, "
#else
    "gtk1, "
#endif
#endif
#ifdef __WXDEBUG__
    "wx-assertions-on, "
#else
    "wx-assertions-off, "
#endif
    "phoenix";


void wxPyCoreModuleInject()
{
    wxInitAllImageHandlers();
}
