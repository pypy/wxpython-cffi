def run(module):

    module.addPyCode('''\
    from ._stc import *
    from . import _stc
    ''', order=0)
