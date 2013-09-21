import etgtools

def run(module):
    c = module.find('wxSizer')

    c.addCppMethod('wxSizerItem*', 'Add', 
                   '(const wxSize& size, int proportion=0, int flag=0, '
                   'int border=0, wxPyUserData* userData /Transfer/ = NULL)',
        doc="Add a spacer using a :class:`Size` object.",
        body="return self->Add(size->x, size->y, proportion, flag, border, userData);")

    c.addCppMethod('wxSizerItem*', 'Prepend', 
                   '(const wxSize& size, int proportion=0, int flag=0, '
                   'int border=0, wxPyUserData* userData /Transfer/ = NULL)',
        doc="Prepend a spacer using a :class:`Size` object.",
        body="return self->Prepend(size->x, size->y, proportion, flag, border, userData);")

    c.addCppMethod('wxSizerItem*', 'Insert', 
                   '(size_t index, const wxSize& size, int proportion=0, int flag=0, '
                   'int border=0, wxPyUserData* userData /Transfer/ = NULL)',
        doc="Insert a spacer using a :class:`Size` object.",
        body="return self->Insert(index, size->x, size->y, proportion, flag, border, userData);")
