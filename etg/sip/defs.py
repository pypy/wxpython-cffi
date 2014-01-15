import etgtools

def run(module):
    # Sip needs these declarations, but cffi assumes them already.
    td = module.find('wxUIntPtr')
    module.insertItemAfter(td, etgtools.TypedefDef(type='unsigned long', name='size_t'))
    module.insertItemAfter(td, etgtools.TypedefDef(type='SIP_SSIZE_T', name='ssize_t'))
    module.insertItemAfter(td, etgtools.TypedefDef(type='SIP_SSIZE_T', name='Py_ssize_t'))
