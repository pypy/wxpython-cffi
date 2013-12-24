from binascii import crc32

from . import utils
from .base import PyObject

from .. import extractors
from ..generators import nci

def create_pycodeblock(pycode, parent):
    PyCodeBlock(pycode, parent)
extractors.PyCodeDef.generate = create_pycodeblock
class PyCodeBlock(PyObject):
    def __init__(self, pycode, parent):
        super(PyCodeBlock, self).__init__(pycode.order, pycode, parent)
        self.code = pycode.code

    def print_pycode(self, userpyfile, indent=0):
        userpyfile.write(nci(self.code, indent))


def create_pyclass(pyclass, parent):
    PyClass(pyclass, parent)
extractors.PyClassDef.generate = create_pyclass
class PyClass(PyObject):
    def __init__(self, pyclass, parent):
        super(PyClass, self).__init__(pyclass.order, pyclass, parent)
        self.pyclass = pyclass

        self.name = pyclass.name
        self.bases = pyclass.bases or ('object')

        for pyobj in pyclass.items:
            pyobj.generate(self)

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("class %s(%s):" % (self.name, self.bases), indent))
        utils.print_docstring(self, pyfile, indent + 4)

        for pyobj in self.pyitems:
            pyobj.print_pycode(pyfile, indent + 4)


def create_pymeth(pymeth, parent):
    PyMethod(pymeth, parent)
extractors.PyMethodDef.generate = create_pymeth
class PyMethod(PyObject):
    def __init__(self, pymeth, parent):
        super(PyMethod, self).__init__(None, pymeth, parent)
        self.pymeth = pymeth
        self.name = pymeth.name
        self.args_string = pymeth.argsString
        self.code = pymeth.body

    def print_pycode(self, pyfile, indent=0):
        tmpname = "_" + hex(crc32(self.parent.unscopedpyname + self.name) &
                            0xffffffff)
        pyfile.write(nci("def %s%s:" % (tmpname, self.args_string), indent))
        utils.print_docstring(self, pyfile, indent + 4)
        pyfile.write(nci(self.code, indent + 4))
        pyfile.write(nci("""\
        {0.parent.unscopedpyname}.{0.name} = {1}
        del {1}""".format(self, tmpname), indent))

def create_pyfuction(pyfunc, parent):
    PyFunction(pyfunc, parent)
extractors.PyFunctionDef.generate = create_pyfuction
class PyFunction(PyObject):
    def __init__(self, pyfunc, parent):
        super(PyFunction, self).__init__(pyfunc.order, pyfunc, parent)
        self.pyfunc = pyfunc

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci('def {0.name}{0.argsString}:'.format(self.pyfunc), indent))
        utils.print_docstring(self, pyfile, indent + 4)
        pyfile.write(nci(self.pyfunc.body, indent + 4))


def create_pyprop(pyprop, parent):
    # Use two different classes here since the printed code is code is pretty
    # different for the two cases
    if isinstance(parent, PyClass):
        PyClassPyProperty(pyprop, parent)
    else:
        CppClassPyProperty(pyprop, parent)
extractors.PyPropertyDef.generate = create_pyprop
class PyClassPyProperty(PyObject):
    def __init__(self, pyprop, parent):
        super(PyClassPyProperty, self).__init__(None, pyprop, parent)
        self.pyprop = pyprop

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("{0.name} = property({0.getter}, {0.setter})"
                         .format(self.pyprop), indent))

class CppClassPyProperty(PyObject):
    def __init__(self, pyprop, parent):
        super(CppClassPyProperty, self).__init__(None, pyprop, parent)
        self.pyprop = pyprop
        self.name = pyprop.name

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("""\
        {0.parent.unscopedpyname}.{0.name} = property(
            {0.parent.unscopedpyname}.{1.getter},
            {0.parent.unscopedpyname}.{1.setter})
        """.format(self, self.pyprop), indent))



# Theres really not a good place to put this:
extractors.WigCode.generate = lambda x, y: None
