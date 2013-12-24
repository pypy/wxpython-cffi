import functools


class ItemFlags(dict):
    def __init__(self, item):
        if isinstance(item, dict):
            super(ItemFlags, self).__init__(item)
        else:
            super(ItemFlags, self).__init__(dict(
                    pyint=getattr(item, 'pyInt', False),
                    nocopy=getattr(item, 'noCopy', False),
                    array=getattr(item, 'array', False),
                    arraysize=getattr(item, 'arraySize', False),
                    out=getattr(item, 'out', False),
                    inout=getattr(item, 'inOut', False),
                    transfer=getattr(item, 'transfer', False),
                    transfer_back=getattr(item, 'transferBack', False),
                    transfer_this=getattr(item, 'transferThis', False),
                    keepref=getattr(item, 'keepReference', False),
                    factory=getattr(item, 'factory', False),
                    hasdefault=bool(getattr(item, 'default', '')),
                    deprecated=bool(getattr(item, 'deprecated', False)),
                ))

    def __getattr__(self, attr):
        return self[attr]

# TODO: cache instantiations
class TypeInfo(object):
    ARRAY_SIZE_PARAM = '_array_size_'
    OUT_PARAM_SUFFIX = '_ptr'
    PY_RETURN_SUFFIX = '_pyreturnval'
    # Fields that will be setup by CppType.build_typeinfo
    c_type = ""
    c_virt_type = ""
    c_virt_return_type = ""
    cdef_type = ""
    cdef_virt_type = ""
    cdef_virt_return_type = ""
    py_type = ""

    # TODO: cache cpp_type; it shouldn't change over an instance's lifetime
    @property
    def cpp_type(self):
        return (("const " if self.const else "") + self.type.unscopedname +
                '&' * self.refcount + '*' * self.ptrcount)

    def __init__(self, scope, name, flags):
        from basictype import getbasictype

        self.original = name
        self.flags = flags

        self.const = 'const ' in name
        self.ptrcount = name.count('*')
        self.refcount = name.count('&')

        for token in ['const ', '*', '&']:
            name = name.replace(token, '').strip()

        if name in ('WL_Object', 'WL_Self'):
            # WL_Object is a special case. This type is used only for Python
            # arguments lists.
            return

        type = getbasictype(name, self)
        if type is None:
            type = scope.gettype(name)
        if type is None:
            scope.module.new_opaque_type(name)
            type = scope.gettype(name)
        self.type = type
        type.build_typeinfo(self)

    def __eq__(self, other):
        if not isinstance(other, TypeInfo):
            return False
        return (self.type == other.type and
                self.const == other.const and
                self.ptrcount == other.ptrcount and
                self.refcount == other.refcount)

    def __getattr__(self, attr):
        attr = getattr(self.type, attr)
        if callable(attr):
           return functools.partial(attr, self)
        else:
            return attr


class CppObject(object):
    def __init__(self, item, parent):
        self.item = item
        self.parent = parent

        self.name = item.name
        self.pyname = getattr(item, 'pyName', '') or item.name
        self.cname = parent.cscopeprefix + self.pyname
        self.unscopedname = parent.scopeprefix + self.name
        self.unscopedpyname = parent.pyscopeprefix + self.pyname

        self.flags = ItemFlags(item)
        parent.add_object(self)

    def setup(self):
        pass

    def print_cdef(self, pyfile):
        pass

    def print_cdef_and_verify(self, pyfile):
        pass

    def print_pycode(self, pyfile, indent=0):
        pass

    def print_headercode(self, hfile):
        pass

    def print_cppcode(self, cppfile):
        pass

    def __repr__(self):
        return "<%s: '%s'>" % (type(self).__name__, self.name)

class CppScope(object):
    def __init__(self, parent):
        self.objects = []
        self.types = []
        self.typescache = { }
        self.subscopes = []
        self.subscopescache = { }

        self.parent = parent
        self.scopeprefix = ''
        self.cscopeprefix = ''
        self.pyscopeprefix = ''

        if parent is not None:
            self.module = parent.module
            parent.add_subscope(self)

    def print_nested_cdef(self, pyfile):
        for type in self.types:
            type.print_cdef(pyfile)
        for obj in self.objects:
            obj.print_cdef(pyfile)
        for scope in self.subscopes:
            scope.print_nested_cdef(pyfile)

    def print_nested_cdef_and_verify(self, pyfile):
        for type in self.types:
            type.print_cdef_and_verify(pyfile)
        for obj in self.objects:
            obj.print_cdef_and_verify(pyfile)
        for scope in self.subscopes:
            scope.print_nested_cdef_and_verify(pyfile)

    # Note this isn't print_nested_pycode. Scopes need to have Python
    # representation.
    def print_pycode(self, pyfile, indent=0):
        pass

    def print_nested_headercode(self, hfile):
        for type in self.types:
            type.print_headercode(hfile)
        for obj in self.objects:
            obj.print_headercode(hfile)
        for scope in self.subscopes:
            scope.print_nested_headercode(hfile)

    def print_nested_cppcode(self, cppfile):
        for type in self.types:
            type.print_cppcode(cppfile)
        for obj in self.objects:
            obj.print_cppcode(cppfile)
        for scope in self.subscopes:
            scope.print_nested_cppcode(cppfile)

    def gettype(self, name):
        type = None

        # Check if the type is declared in this scope directly
        if name in self.typescache:
            type = self.typescache[name]

        # Check if it is in one of the scoped nested in this one
        if '::' in name and type is None:
            scope, splitname = name.split('::', 1)
            if scope in self.subscopescache:
                type = self.subscopescache[scope].gettype(splitname)

        # Check if it is in the parent's scope
        if self.parent is not None and type is None:
            type = self.parent.gettype(name)

        # Add the (full) name to this scope's list so future looks will be
        # faster (most types are referenced either many times or none)
        self.typescache[name] = type

        return type

    def setup_types(self):
        self.print_order = []
        for scope in self.subscopes:
            scope.setup_types()
        for type in self.types:
            type.setup()

    def setup_objects(self):
        for obj in self.objects:
            obj.setup()
        for scope in self.subscopes:
            scope.setup_objects()

    def add_object(self, obj):
        self.objects.append(obj)

    def add_type(self, type):
        self.types.append(type)
        self.typescache[type.name] = type

    def add_subscope(self, scope):
        self.subscopes.append(scope)
        self.subscopescache[scope.name] = scope

    def append_to_printing_order(self, obj):
        """
        Objects that are passed to this method will have their print_pycode
        method called before other objects and in the order they are added.

        Note that objects that are in the printing_order list will have their
        print_pycode method called more than once.
        """
        self.print_order.append(obj)

class CppType(object):
    def __init__(self, item, parent):
        self.item = item
        self.name = item.name
        self.pyname = getattr(item, 'pyName', '') or item.name
        self.cname = parent.cscopeprefix + self.pyname
        self.parent = parent

        self.unscopedname = parent.scopeprefix + self.name
        self.unscopedpyname = parent.pyscopeprefix + self.pyname

        self.flags = ItemFlags(item)

        parent.add_type(self)

    def setup(self):
        pass

    def print_cdef(self, pyfile):
        pass

    def print_cdef_and_verify(self, pyfile):
        pass

    def print_pycode(self, pyfile, indent=0):
        pass

    def print_finalize_pycode(self, pyfile):
        pass

    def print_headercode(self, hfile):
        pass

    def print_cppcode(self, cppfile):
        pass

    def build_typeinfo(self, typeinfo):
        pass


    # Conversion methods (python code):

    def call_cdef_param_setup(self, typeinfo, name):
        pass

    def call_cdef_param_inline(self, typeinfo, name):
        return name

    def call_cdef_param_cleanup(self, typeinfo, name):
        pass

    def virt_py_param_setup(self, typeinfo, name):
        pass

    def virt_py_param_inline(self, typeinfo, name):
        return name

    def virt_py_param_cleanup(self, typeinfo, name):
        pass

    def virt_py_return(self, typeinfo, name):
        pass

    # Conversion methods (c++ code):

    def call_cpp_param_setup(self, typeinfo, name):
        pass

    def call_cpp_param_inline(self, typeinfo, name):
        return name

    def call_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_param_setup(self, typeinfo, name):
        pass

    def virt_cpp_param_inline(self, typeinfo, name):
        return name

    def virt_cpp_param_cleanup(self, typeinfo, name):
        pass

    def virt_cpp_return(self, typeinfo, name):
        return name

    def convert_variable_cpp_to_c(self, typeinfo, name):
        pass

    def convert_variable_c_to_py(self, typeinfo, name):
        pass

    def __repr__(self):
        return "<%s: '%s'>" % (type(self).__name__, self.name)


class PyObject(object):
    def __init__(self, order, pyobj, parent):
        if isinstance(parent, PyObject):
            # This gets printed inside the enclosing PyObject instead in the
            # top-level scope.
            parent.pyitems.append(self)
        else:
            parent.module.pyitems.append(self)
        self.order = order
        self.parent = parent
        self.pyitems = []

        self.docstring = getattr(pyobj, 'briefDoc', False) or ''

    def print_pycode(self, userpyfile, indent=0):
        pass

