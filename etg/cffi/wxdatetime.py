import etgtools
import sys

def run(module):
    if sys.platform == 'win32':
        module.cdefs_cffi.append('typedef long long time_t;')
        module.find('time_t').ignore()
    module.addItem(etgtools.DefineDef(name='wxLOCALE_LOAD_DEFAULT', value=''))
