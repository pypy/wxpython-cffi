from .base import args_string, SelfParam, FunctionBase, VoidType
from .operators import get_standalone_operator

class Function(FunctionBase):
    PREFIX = 'wrappedfunc_'
    def __init__(self, func, parent):
        super(Function, self).__init__(func, parent)

        operator = get_standalone_operator(self)
        if operator is not None:
            class_name, self.operator = operator
            self.parent = parent.gettype(class_name)
            self.pyname = self.operator.pyname
            self.cname = self.cname[:-len(self.name)] + self.pyname

    @property
    def call_cpp_code(self):
        code = ''
        if not isinstance(self.type.type, VoidType):
            code = '{0.type.cpp_type} cppreturnval = '.format(self)

        if self.cppcode:
            code += ('{0.wrapper_call_code};\n'.format(self))
        else:
            code += '{0.name}{0.call_cpp_args};\n'.format(self)
        return code
        
