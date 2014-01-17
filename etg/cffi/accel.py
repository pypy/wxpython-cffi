from etgtools import CppMethodDef_cffi, ArgsString

def run(module):
    c = module.find('wxAcceleratorTable')

    # Replace the implementation of the AcceleratorTable ctor so it can
    # accept a Python sequence of tuples or AcceleratorEntry objects like
    # Classic does. Using the arraySize and array annotations does let us
    # pass a list of entries, but they have to already be AccelertorEntry
    # obejcts. We want to allow Items in the list to be either
    # wx.AcceleratorEntry items or a 3-tuple containing the values to pass to
    # the wx.AcceleratorEntry ctor.

    c.addItem(CppMethodDef_cffi(
        'wxAcceleratorTable', ArgsString('(WL_Self self, WL_Object entries)'),
        """\
        errmsg = "Expected a sequence of 3-tuples or wx.AcceleratorEntry objects."
        if not isinstance(entries, (collections.Sequence)):
            raise TypeError(errmsg)

        cdata = ffi.new('int[]', len(entries) * 3)
        keepalive = []

        for i, entry in enumerate(entries):
            if isinstance(entry, _core.AcceleratorEntry):
                cdata[i * 3]     = entry.GetFlags()
                cdata[i * 3 + 1] = entry.GetKeyCode()
                cdata[i * 3 + 2] = entry.GetCommand()
            else:
                if (not isinstance(entry, collections.Sequence) or
                    len(entry) != 3 or
                    any(not isinstance(i, numbers.Number) for i in entry)):
                    raise TypeError(errmsg)
                cdata[i * 3]     = int(entry[0])
                cdata[i * 3 + 1] = int(entry[1])
                cdata[i * 3 + 2] = int(entry[2])

        ptr = call(len(entries), cdata)
        wrapper_lib.init_wrapper(self, ptr, wrapper_lib.hassubclass(type(self)))
        """,

        'void*', '(int len, int* entries_args)',
        """\
        wxAcceleratorEntry *entries = new wxAcceleratorEntry[len];
        for(int i = 0; i < len; i++)
            entries[i].Set(entries_args[i * 3],
                           entries_args[i * 3 + 1],
                           entries_args[i * 3 + 2]
            );
        WL_CLASS_NAME *selfptr = new WL_CLASS_NAME(len, entries);
        delete[] entries;
        return selfptr;
        """,
        originalCppArgs=ArgsString('(int n, const wxAcceleratorEntry entries[])'),
        briefDoc="TODO",
        isCtor=True))
