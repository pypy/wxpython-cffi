def run(module):

    module.addPyCode('''\
    from ._grid import *
    from . import _grid
    ''', order=0)
