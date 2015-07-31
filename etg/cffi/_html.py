def run(module):

    module.addPyCode('''\
    from ._html import *
    from . import _html
    ''', order=0)
