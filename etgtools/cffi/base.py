class flags(dict):
    def __init__(self, item):
        # TODO: add more flags?
       super(flags, self).__init__(dict(
            pyint=getattr(item, 'pyInt', False),
            array=getattr(item, 'array', False),
            arraysize=getattr(item, 'arraySize', False),
            out=getattr(item, 'out', False),
            inout=getattr(item, 'inOut', False),
            transfer=getattr(item, 'transfer', False),
            factory=getattr(item, 'factory', False),
        ))

    def __getattr__(self, attr):
        return self[attr]


class CppObject(object):
    def __init__(self, item, parent):
        self.item = item
        self.parent = parent

        self.name = item.name
        self.pyname = item.pyName
        self.unscopedname = parent.scopeprefix + self.name
        self.unscopedpyname = parent.pyscopeprefix + self.pyname

        self.flags = flags(item)
        parent.add_object(self)

    def setup(self):
        pass

    def print_cdef(self, pyfile):
        pass

    def print_pycode(self, pyfile):
        pass

    def print_headercode(self, hfile):
        pass

    def print_cppcode(self, cppfile):
        pass

class CppScope(object):
    def __init__(self, parent):
        self.objects = []
        self.types = []
        self.typescache = { }
        self.subscopes = { }

        self.parent = parent
        self.scopeprefix = ''
        self.pyscopeprefix = ''

        if parent is not None:
            self.module = parent.module
            parent.add_subscope(self)

    def gettype(self, name):
        type = None

        # Check if the type is declared in this scope directly
        if name in self.typescache:
            type = self.typescache[name]

        # Check if it is in one of the scoped nested in this one
        if '::' in name and type is None:
            scope, splitname = name.split('::', 1)
            if scope in self.subscopes:
                type = self.subscopes[scope].gettype(splitname)

        # Check if it is in the parent's scope
        if self.parent is not None and type is None:
            type = self.parent.gettype(name)

        # Add the (full) name to this scopes list so future looks will be
        # faster (most types are referenced either many times or none)
        self.typescache[name] = type

        return type

    def setup_types(self):
        self.finalized_types = []
        for scope in self.subscopes.itervalues():
            scope.setup_types()
        for type in self.types:
            type.setup()

    def setup_objects(self):
        for obj in self.objects:
            obj.setup()
        for scope in self.subscopes.itervalues():
            scope.setup_objects()

    def add_object(self, obj):
        self.objects.append(obj)

    def add_type(self, type):
        self.types.append(type)
        self.typescache[type.name] = type

    def add_subscope(self, scope):
        self.subscopes[scope.name] = scope

    def finalized_type(self, type):
        # Wrapped classes will call this method after they have finished
        # setting up. This is list is used to order when they are printed
        if type.parent is self:
            self.finalized_types.append(type)

class CppType(object):
    def __init__(self, item, parent):
        self.item = item
        self.name = item.name
        self.pyname = getattr(item, 'pyName', '') or item.name
        self.parent = parent

        self.unscopedname = parent.scopeprefix + self.name
        self.unscopedpyname = parent.pyscopeprefix + self.pyname

        self.flags = flags(item)

        parent.add_type(self)

    def setup(self):
        pass

class PyObject(object):
    def __init__(self, item, parent):
        pass

    def print_pycode(self, userpyfile):
        pass
