from .base import CppObject, TypeInfo
from .function import Method

from . import utils

from .. import extractors
from ..generators import nci

# MemberVariables are very different from global variables, so they are in
# their own module.


class MemberVariable(CppObject):
    def __init__(self, item, parent):
        getter = extractors.MethodDef(
            type=item.type, name='_mvargetter_' + item.pyName,
            cppCode=('return self->%s;' % item.name, 'function'))
        getter.generate(parent)

        setter = extractors.MethodDef(
            type='void', name='_mvarsetter_' + item.pyName,
            items=[extractors.ParamDef(type=item.type, name='value')],
            cppCode=('self->%s = value;' % item.name, 'function'))
        setter.generate(parent)

        super(MemberVariable, self).__init__(item, parent)

    def print_pycode(self, pyfile, indent=0):
        pyfile.write(nci("""\
        {0.pyname} = property(_mvargetter_{0.pyname},
                              _mvarsetter_{0.pyname})
        del _mvargetter_{0.pyname}
        del _mvarsetter_{0.pyname}
        """.format(self), indent))


def create_mvar(mvar, parent):
    MemberVariable(mvar, parent)
extractors.MemberVarDef.generate = create_mvar
