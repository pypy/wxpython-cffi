def run(module):

    module.addPyCode('''\
    from ._adv import *
    from . import _adv
    ''', order=0)
