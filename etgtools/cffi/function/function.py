from .base import args_string, SelfParam, FunctionBase, VoidType

class Function(FunctionBase):
    PREFIX = 'wrappedfunc_'
    def __init__(self, func, parent):
        super(Function, self).__init__(func, parent)

    @args_string
    def py_types_args(self):
        for param in self.params:
            if isinstance(param, SelfParam) or param.flags.arraysize:
                continue
            if self.overload_manager.is_overloaded():
                yield "%s=%s" % (param.name, param.type.py_type)
            else:
                yield '("{0.name}", {0.type.py_type}, {0.name})'.format(param)

    @property
    def call_cpp_code(self):
        code = ''
        if not isinstance(self.type.type, VoidType):
            code = '{0.type.cpp_type} cppreturnval = '.format(self)

        if self.cppcode:
            code += ('{0.WRAPPER_PREFIX}{0.cname}{0.call_cpp_args};\n'
                     .format(self))
        else:
            code += '{0.name}{0.call_cpp_args};\n'.format(self)
        return code
