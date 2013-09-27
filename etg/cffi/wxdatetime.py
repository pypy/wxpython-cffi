import etgtools
import sys

def run(module):
    module.addItem(etgtools.DefineDef(name='wxLOCALE_LOAD_DEFAULT', value=''))
