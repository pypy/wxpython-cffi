from .base import CppType

from .. import extractors

"""
How sip seems to handle templates:
    sip doesn't instantiate templates unless a typedef is provided for them.
    This sort of makes sense from a Python syntax point of view anyway...

    It looks like it replaces all of the template arguments's with the provided
    name. Its not obvious if non-typename template arguments are supported, but
    its not unreasonable to delay their implementation I think...
"""

class Typedef(CppType):
    def __init__(self, typedef, parent):
        super(Typedef, self).__init__(typedef, parent)

    def gettypeinfo(self, original, name, flags):
        pass

#----------------------------------------------------------------------------#

def generate_typedef(typedef, parent):
    Typedef(typedef, parent)
extractors.TypedefDef.generate = generate_typedef
