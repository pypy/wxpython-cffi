import cppwrapper

class ObjectRegistry(object):
    def __init__(self):
        self.map = {}

    def obj_from_ptr(self, ptr, klass=object):
        if not ptr in self.map:
            # TODO: allow a callback to check if this object is more
            #       specialized than klass
            obj = klass._from_ptr(ptr)
            self.map[ptr] = obj
            return obj
        else:
            return self.map[ptr]

    def register_ptr(self, obj):
        if not isinstance(obj, CppWrapper):
            raise TypeError("")

        if not ptr in self.map:
            self.map[obj._cpp_ptr] = obj
        else:
            # TODO: check if type(obj) is in the mro of the stored object
            pass

    def remove_ptr(self, ptr):
        # TODO: remove child objects if necissary
        del self.map[ptr]

    def take_ownership(self, obj):
        pass

    def give_ownership(self, obj, parent=None):
        pass

object_registry = ObjectRegistry()
