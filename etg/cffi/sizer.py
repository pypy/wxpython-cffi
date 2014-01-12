import etgtools
from etgtools import ArgsString

def run(module):
    c = module.find('wxSizer')

    c.addMethod(
        'wxSizerItem*', 'Add',
        ArgsString('(const wxSize& size, int proportion=0, int flag=0,'
                   ' int border=0, wxPyUserData* userData = NULL)')
                   .annt('userData', 'transfer'),
        doc="Add a spacer using a :class:`Size` object.",
        cppCode=("return self->Add(size->x, size->y, proportion, flag, border, userData);",
                 'function'))

    c.addMethod(
        'wxSizerItem*', 'Prepend',
        ArgsString('(const wxSize& size, int proportion=0, int flag=0,'
                   ' int border=0, wxPyUserData* userData = NULL)')
                   .annt('userData', 'transfer'),
        doc="Prepend a spacer using a :class:`Size` object.",
        cppCode=("return self->Prepend(size->x, size->y, proportion, flag, border, userData);",
                 'function'))

    c.addMethod(
        'wxSizerItem*', 'Insert',
        ArgsString('(size_t index, const wxSize& size, int proportion=0,'
                   ' int flag=0, int border=0, wxPyUserData* userData = NULL)')
                   .annt('userData', 'transfer'),
        doc="Insert a spacer using a :class:`Size` object.",
        cppCode=("return self->Insert(index, size->x, size->y, proportion, flag, border, userData);",
                 'function'))
