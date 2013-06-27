from registry import object_registry

class CppWrapper(object):
    _ffi = None
    _lib = None
    _vtable = None

    def __init__(self, cpp_obj, py_owned=False):
        self._cpp_obj = cpp_obj if cpp_obj is not None else self._ffi.NULL
        self._py_owned = py_owned

    @classmethod
    def _from_ptr(cls, ptr):
        obj = cls.__new__(cls)
        CppWrapper.__init__(obj, ptr, False)
        return obj


def global_dtor(ptr):
    pass

def wrapper_class(ffi, lib, vtable=None, virtual_methods=None):
    if ((vtable is None and virtual_methods is not None) or
        (vtable is not None and virtual_methods is None)):
        raise ValueError('Either both or neither vtable and  virtual_methods '
                         'may None')

    def closure(cls_name, cls_bases, cls_attrs):
        cls_attrs['_ffi'] = ffi
        cls_attrs['_lib'] = lib
        cls_attrs['_vtable'] = vtable

        # Setup the global wrapper dtor
        if vtable is not None:
            if not hasattr(ffi, 'global_dtor'):
                ffi.global_dtor = ffi.callback("void(void*)", global_dtor)
            vtable[0] = ffi.cast('void(*)()', ffi.global_dtor)

        # Create callbacks to populate the vtable
        for key, method in cls_attrs.iteritems():
            if not hasattr(method, '_virtual_method'):
                continue
            idx = method._virtual_method
            cb = ffi.callback(virtual_methods[idx], method)
            cls_attrs[key] = cb
            vtable[idx] = ffi.cast('void(*)()', cb)

        return type(cls_name, cls_bases, cls_attrs)

    return closure

def virtual_method(idx):
    def closure(func):
        func._virtual_method = idx
        return func
    return closure
