def wrapper_class(ffi, lib, vtable_func=None, virtual_methods=None):
    if ((vtable_func is None and virtual_methods is not None) or
        (vtable_func is not None and virtual_methods is None)):
        raise ValueError('Either both or neither vtable_func and '
                         'virtual_methods may None')

    def closure(cls_name, cls_bases, cls_attrs):
        cls_attrs['_ffi'] = ffi
        cls_attrs['_lib'] = lib
        if virtual_methods is not None:
            cls_attrs['_vtable'] = ffi.new('void(*[])()', len(virtual_methods))
            vtable_func(cls_attrs['_vtable'])

        # Create callbacks to populate the vtable
        for key, method in cls_attrs.iteritems():
            if not hasattr(method, '_virtual_method'):
                continue
            idx = method._virtual_method
            method = ffi.callback(virtual_methods[idx], method)
            cls_attrs['_vtable'][idx] = ffi.cast('void(*)()', method)

        return type(cls_name, cls_bases, cls_attrs)

    return closure

def virtual_method(idx):
    def closure(func):
        func._virtual_method = idx
        return func
    return closure


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
