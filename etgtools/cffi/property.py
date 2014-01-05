from . import utils
from .base import CppObject

from .. import extractors
from ..generators import nci


def create_property(prop, parent):
    Property(prop, parent)
extractors.PropertyDef.generate = create_property

class Property(CppObject):
    def __init__(self, prop, parent):
        super(Property, self).__init__(prop, parent)
        self.prop = prop
        self.name = prop.name

    def print_pycode(self, pyfile, indent=0):
        setter = ''
        if self.prop.setter:
            setter = 'lambda self, x: self.%s(x)' % self.prop.setter

        pyfile.write(nci("""\
        {0.name} = property(lambda self: self.{0.prop.getter}(), {1})
        """.format(self, setter), indent))
