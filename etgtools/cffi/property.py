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
        pyfile.write(nci("""\
        {0.name} = property({1.getter}, {1.setter})
        """.format(self, self.prop), indent))
