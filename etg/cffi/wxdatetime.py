import etgtools
import sys

def run(module):
    if sys.platform == 'win32':
        module.cdefs_cffi.append('typedef long long time_t;')
    else:
        module.cdefs_cffi.append('typedef long time_t;')
    module.addItem(etgtools.DefineDef(name='wxLOCALE_LOAD_DEFAULT', value=''))
