from .method import utils, nci, VoidType, Method, SelfParam, OverloadManager

class StaticMethodOverloadManager(OverloadManager):
    @utils.call_once
    def print_pycode(self, pyfile, indent):
        pyfile.write(nci("@staticmethod", indent))

        super(StaticMethodOverloadManager, self).print_pycode(pyfile, indent)

class StaticMethod(Method):
    OVERLOAD_MANAGER = StaticMethodOverloadManager
    def __init__(self, meth, parent):
        super(StaticMethod, self).__init__(meth, parent)

        # For ownership transfer purposes, static methods just like global
        # functions.
        self.ownership_transfer_name = 'None'
        self.keepref_on_object = False
        if self.flags.factory:
            self.ownership_transfer_name = 'creturnval'
            self.keepref_on_object = True

        self.params = [p for p in self.params if not isinstance(p, SelfParam)]

    @property
    def call_cpp_code(self):
        if self.cppcode:
            return super(StaticMethod, self).call_cpp_code

        code = ''
        if not isinstance(self.type.type, VoidType):
            code = '{0.type.cpp_type} cppreturnval = '.format(self)

        return code +('{0.parent.cppname}::{0.name}{0.call_cpp_args};\n'
                      .format(self))

    def print_headercode(self, hfile):
        # No header code should be needed for public static methods.
        if self.protection == 'public':
            return

        hfile.write(nci("""\
        static {0.type.cpp_type} {0.name}{0.cpp_args}
        {{""".format(self), 4))

        hfile.write(' ' * 8)
        if not isinstance(self.type.type, VoidType):
            hfile.write('return ')

        hfile.write("{0.parent.unscopedname}::{0.name}{0.call_original_cpp_args};\n"
                    .format(self))
        hfile.write('    }\n')
