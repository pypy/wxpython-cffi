def run(module):
    pass
    # TODO: everything sip/dataobj.py. In particular, there are a large number
    #       of CppMethods that have CPython specific code, or worse, virtual
    #       catchers that need to be replaced

    #------------------------------------------------------------
    c = module.find('wxDataObjectSimple')


    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')

    #------------------------------------------------------------
    c = module.find('wxDataObjectComposite')

    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')

    #------------------------------------------------------------
    c = module.find('wxURLDataObject')

    # We need to let the generator know that the pure virtuals in the base
    # class have impelmentations here even though they will not be used much
    # (if at # all.) Those that are overridden in this class with different
    # signatures we'll just mark as private to help avoid confusion.
    c.addMethod('size_t', 'GetDataSize', '(const wxDataFormat& format)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'GetDataHere', '(const wxDataFormat& format, void* buf)',
                isVirtual=True, isConst=True, protection='private')
    c.addMethod('bool', 'SetData',
                '(const wxDataFormat& format, size_t len, const void* buf)',
                isVirtual=True, protection='private')
