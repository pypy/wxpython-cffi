import etgtools

def run(module):
    c = module.find('wxSizer')

    c.addMethod(
        'wxSizerItem*', 'Add',
       '(const wxSize& size, int proportion=0, int flag=0, '
       'int border=0, wxPyUserData* userData = NULL)',
        items=[
            etgtools.ParamDef(type='const wxSize&', name='size'),
            etgtools.ParamDef(type='int', name='proportion', default='0'),
            etgtools.ParamDef(type='int', name='flag', default='0'),
            etgtools.ParamDef(type='int', name='border', default='0'),
            etgtools.ParamDef(type='wxPyUserData*', name='userData',
                              default='NULL', transfer=True)],
        doc="Add a spacer using a :class:`Size` object.",
        cppCode=("return self->Add(size->x, size->y, proportion, flag, border, userData);",
                 'function'))

    c.addMethod(
        'wxSizerItem*', 'Prepend',
        '(const wxSize& size, int proportion=0, int flag=0, '
        'int border=0, wxPyUserData* userData = NULL)',
        items=[
            etgtools.ParamDef(type='const wxSize&', name='size'),
            etgtools.ParamDef(type='int', name='proportion', default='0'),
            etgtools.ParamDef(type='int', name='flag', default='0'),
            etgtools.ParamDef(type='int', name='border', default='0'),
            etgtools.ParamDef(type='wxPyUserData*', name='userData',
                              default='NULL', transfer=True)],
        doc="Prepend a spacer using a :class:`Size` object.",
        cppCode=("return self->Prepend(size->x, size->y, proportion, flag, border, userData);",
                 'function'))

    c.addMethod(
        'wxSizerItem*', 'Insert',
        '(size_t index, const wxSize& size, int proportion=0, int flag=0, '
        'int border=0, wxPyUserData* userData = NULL)',
        items=[
            etgtools.ParamDef(type='size_t', name='index'),
            etgtools.ParamDef(type='const wxSize&', name='size'),
            etgtools.ParamDef(type='int', name='proportion', default='0'),
            etgtools.ParamDef(type='int', name='flag', default='0'),
            etgtools.ParamDef(type='int', name='border', default='0'),
            etgtools.ParamDef(type='wxPyUserData*', name='userData',
                              default='NULL', transfer=True)],
        doc="Insert a spacer using a :class:`Size` object.",
        cppCode=("return self->Insert(index, size->x, size->y, proportion, flag, border, userData);",
                 'function'))
