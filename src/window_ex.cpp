
#ifdef __WXMSW__
#include <wx/msw/private.h>
#endif

#ifdef __WXGTK__
#include <gdk/gdkx.h>
#include <gtk/gtk.h>
#include <wx/gtk/private/win_gtk.h>
#define GetXWindow(wxwin) (wxwin)->m_wxwindow ? \
                          GDK_WINDOW_XWINDOW((wxwin)->m_wxwindow->window) : \
                          GDK_WINDOW_XWINDOW((wxwin)->m_widget->window)
#endif





wxUIntPtr wxPyGetWinHandle(const wxWindow* win) 
{
#ifdef __WXMSW__
    return (wxUIntPtr)win->GetHandle();
#endif
#if defined(__WXGTK__) || defined(__WXX11__)
    return (wxUIntPtr)GetXWindow(win);
#endif
#ifdef __WXMAC__
    return (wxUIntPtr)win->GetHandle();
#endif
    return 0;
}
