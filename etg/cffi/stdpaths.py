def run(module):
    c = module.find('wxStandardPaths')

    # The sip backend always uses a pointer to return wxStrings from custom
    # code wrappers. For the time being, the cffi backend does not (because
    # I don't understand why the sip backend does this and I'm not willing to
    # make a special case for one type.) So, change these methods so they
    # return a value instead of a pointer.

    c.find('MSWGetShellDir').setCppCode("""\
    #ifdef __WXMSW__
        return wxString(wxStandardPaths::MSWGetShellDir(csidl));
    #else
        return wxString();
    #endif
    """)
    
    c.find('GetInstallPrefix').setCppCode("""\
    #ifdef __WXMSW__
        return wxString();
    #else
        return wxString(self->GetInstallPrefix());
    #endif
    """)
