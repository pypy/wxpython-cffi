# Import all of these modules so the generate methods get added onto the
# original extactor classes
import wrappedtype
import mappedtype
import function
import enum

from base import CppScope

from .. import extractors

class Module(CppScope):
    def __init__(self, module, imported_modules):
        super(Module, self).__init__(None)

        self.module = self
        self.imported_modules = imported_modules

        self.name = module.name
        self.cname = module.name
        self.pyname = module.name
        self.scopeprefix = ''
        self.pyscopeprefix = self.name + '.'

        # Items will add themselves to the items list as they're generated
        for item in module.items:
            item.generate(self)

    def setup(self):
        # Setup any modules this one depends on
        for mod in self.imported_modules:
            mod.setup()

        self.setup_types()
        self.setup_objects()

    def gettype(self, name):
        type = super(Module, self).gettype(name)
        if type is not None:
            return type

        for mod in [self] + self.imported_modules:
            type = mod.gettype(name)
            if type is not None:
                self.typescache[name] = type
                return type

        return None

    def gettypeinfo(self, name, **kwargs):
        try:
            return TypeInfo.new(name, self.gettypeinfo, **kwargs)
        except UnknownTypeException as e:
            warnings.warn("Encountered unknown type '%s'. Creating opaque type"
                          % e.type)
            self.new_opaque_type(e.type)
            return self.gettype(name, **kwargs)

    def new_opqaue_type(self, typeName):
        c = extractors.ClassDef(name=typeName)
        c.generate(c)
