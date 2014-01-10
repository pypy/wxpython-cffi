from .method import nci, Method, Param, SelfParam, InheritedVirtualMethodMixin

# TODO: sip supports custom C++ code for dtors, although wxPython doesn't make
#       use of it. Maybe its worthwhile to have anyway?

from ...extractors import MethodDef

class DtorMethod(Method):
    def __init__(self, meth, parent):
        if not meth.type:
            meth.type = 'void'
        super(DtorMethod, self).__init__(meth, parent)
        self.pyname = '__del__'
        self.cname = self.cname[:-len(self.name)] + self.pyname

    def print_headercode(self, hfile):
        if not self.virtual:
            # Every class should have a dtor, but we only want to print the
            # declaration in classes with virtual dtors.
            return
        hfile.write("    virtual ~{0.parent.cppname}();\n".format(self))

    def print_pycode(self, pyfile, indent):
        # The call is wrapped in a try block with a bare-except here to silence
        # errors messages on interpreter exit (wrapper_lib, in part or whole,
        # may not exist when __del__ is called.)
        pyfile.write(nci("""\
        def __del__(self):
            try:
                if self._py_owned:
                    clib.{0.cname}(wrapper_lib.obj_from_ptr(self))
            except:
                pass
        """.format(self), indent))

        if self.virtual:
            pyfile.write(nci("""\
            _virtual__{0.vtable_index} = wrapper_lib.VirtualDispatcher({0.vtable_index})(None)
            """.format(self), indent))

    def print_cppcode(self, cppfile):
        del_stmt = "delete self"
        if self.protection == 'private':
            del_stmt = ''

        cppfile.write(nci("""\
        WL_C_INTERNAL void {0.cname}({0.parent.cppname} *self)
        {{
            {1};
        }}""".format(self, del_stmt)))

        if self.virtual and not self.parent.uninstantiable:
            self.print_virtual_cppcode(cppfile)

    def print_virtual_cppcode(self, cppfile):
        cppfile.write(nci("""\
        typedef void (*{0.cname}_funcptr)({0.parent.cppname} *);
        {0.parent.cppname}::~{0.parent.cppname}()
        {{
            (({0.cname}_funcptr){0.parent.cname}_vtable[{0.vtable_index}])(this);
        }}""".format(self)))

    @staticmethod
    def new_std_dtor(cls, virtual=False, protection='public'):
        dtor = MethodDef(type='void', name='~' + cls.name, isDtor=True,
                         isVirtual=virtual, protection=protection)
        dtor.generate(cls).setup()

    def copy_onto_subclass(self, cls):
        if not any(isinstance(m, DtorMethod) for m in cls.objects):
            self.new_std_dtor(cls, self.virtual, self.protection)
