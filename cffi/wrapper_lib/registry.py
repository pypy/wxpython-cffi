class ObjectRegistry(object):
    def __init__(self):
        self.map = {}

    def obj_from_ptr(self, ptr, klass=object):
        pass

    def register_ptr(self, ptr, obj):
        pass

    def remove_ptr(self, ptr):
        pass

    def take_ownership(self, obj):
        pass

    def give_ownership(self, obj, parent=None):
        pass

object_registry = ObjectRegistry()
