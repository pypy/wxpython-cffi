from .base import args_string, SelfParam, FunctionBase, VoidType

class Function(FunctionBase):
    PREFIX = 'wrappedfunc_'
    def __init__(self, func, parent):
        super(Function, self).__init__(func, parent)

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
