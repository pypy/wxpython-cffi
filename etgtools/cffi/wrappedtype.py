from .base import CppType, CppScope

from .. import extractors

def create_wrappedtype(mtype, parent):
    WrappedType(mtype, parent)
extractors.ClassDef.generate = create_wrappedtype

class WrappedType(CppType, CppScope):
    def __init__(self, cls, parent):
        self._setup_completed = False

        CppType.__init__(self, cls, parent)
        CppScope.__init__(self, parent)

        for klass in cls.innerclasses:
            WrappedType(klass, self)

    def setup(self):
        self.setup_types()

    def setup_types(self):
        if self._setup_completed:
            return
        self._setup_completed = True
        if isinstance(self.parent, WrappedType):
            # If this is a nested class, always setup the outer class first so
            # that this class will appear before any of its subclasses in the
            # Python file
            self.parent.setup()

        self.bases = []
        for basename in self.item.bases:
            base = self.parent.gettype(basename)
            if base is None:
                raise ValueError("Unable to locate base class '%s' for class "
                                 "'%s'" % (basename, self.name))
            base.setup()
            self.bases.append(base)

        super(WrappedType, self).setup_types()

        self.parent.finalized_type(self)

    def gettype(self, name):
        type = super(WrappedType, self).gettype(name)
        if type is not None:
            return type

        # Check for the type in base classes too
        for base in self.bases:
            type = base.gettype(name)
            if type is not None:
                return type

        return None
