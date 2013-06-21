class Multimethod(object):
    def __init__(self):
        pass

    def overload(self, *args, **kwargs):
        def closure(func):
            return self
        return closure

    def __call__(self, *args, **kwargs):
        return None
