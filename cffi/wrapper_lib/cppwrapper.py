import weakref


class CppWrapper(object):
    _ffi = None
    _lib = None
    _vtable = None

    def __init__(self, cpp_obj, py_owned=True):
        self._cpp_obj = cpp_obj if cpp_obj is not None else self._ffi.NULL
        self._py_owned = py_owned
        remember_ptr(self, self._cpp_obj, py_owned)

        self._parent = None
        self._child = None
        self._next_sibling = None
        self._prev_sibling = None

    def __del__(self):
        if not self._py_owned:
            forget_ptr(self._cpp_obj)

    @classmethod
    def _from_ptr(cls, ptr):
        obj = cls.__new__(cls)
        CppWrapper.__init__(obj, ptr, False)
        return obj


def global_dtor(ptr):
    if not ptr in object_map:
        #TODO: raise an exception? This is called via a cffi callback, so the
        #      exception wouldn't propagate to regular python code
        return

    forget_ptr(ptr)

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



cpp_owned_objects = set()
object_map = weakref.WeakValueDictionary()

def obj_from_ptr(ptr, klass=CppWrapper):
    if ptr not in object_map:
        # If an python object for this pointer doesn't yet exist, create one
        obj = klass._from_ptr(ptr)
        object_map[ptr] = obj
        return obj

    obj = object_map[ptr]
    if isinstance(obj, klass):
        return obj

    # If obj isn't an instance of klass but has the same location, one of two
    # things are likely to have happened:
    # 1. The old object was deleted and this is a new object at that same
    #    location
    # 2. The original entry was for superclass of the actual class of obj
    # We'll assume the former case because we don't really have a solution to
    # the latter. That is to say, we'll replace the old object with a new one
    # with the correct class

    old_parent = obj._parent
    obj = klass._from_ptr(ptr)

    if old_parent is not None:
        _detach_from_parent(obj)
        object_map[ptr] = obj
        _attach_to_parent(obj, old_parent())
    else:
        object_map[ptr] = obj
    return obj

def remember_ptr(obj, ptr, weak=False):
    if not weak:
        cpp_owned_objects.add(obj)
    object_map[ptr] = obj

def forget_ptr(ptr):
    if object_map is not None and ptr in object_map:
        obj = object_map[ptr]
        cpp_owned_objects.discard(obj)
        del object_map[ptr]

        _detach_children(obj)
        # TODO: does obj need to detach from its parent too?

def take_ownership(obj):
    obj._py_owned = True
    cpp_owned_objects.discard(obj)
    _detach_from_parent(obj)

def give_ownership(obj, parent=None):
    obj._py_owned = False

    _detach_from_parent(obj)
    if parent is not None:
        # If parent is not None, the parent will hold the reference that keeps
        # obj alive
        _attach_to_parent(obj, parent)
    else:
        # If parent is None, we keep obj alive via cpp_owned_objects
        cpp_owned_objects.add(obj)

def _detach_from_parent(obj):
    if obj._parent is None:
        # No parent to detach from
        return

    parent = obj._parent()
    if parent is None or obj._prev_sibling is None:
        # The parent has been garbage collected, but this object is still
        # attached to it, which shouldn't be possible. Maybe an exception
        # should be thrown?
        return

    if parent._child is obj:
        parent._child = obj._next_sibling
    else:
        # If obj isn't the first child, it has a previous sibling
        obj._prev_sibling()._next_sibling = obj._next_sibling
    if obj._next_sibling is not None:
        obj._next_sibling = obj._prev_sibling

    obj._parent = None
    obj._prev_sibling = None
    obj._next_sibling = None

def _detach_children(obj):
    child = obj._child
    while child is not None:
        next = child._next_sibling
        child._prev_sibling = None
        child._next_sibling = None
        child = next

    obj._child = None

def _attach_to_parent(obj, parent):
    # obj shouldn't already be attached to a parent when this is called

    if parent._child is None:
        obj._parent = weakref.ref(parent)
    else:
        # Don't create a new weakref object if we don't have too
        obj._parent = parent._child._parent

        # obj is being inserted at the front of the list
        parent._child._prev_sibling = weakref.ref(obj)

    obj._next_sibling = parent._child
    parent._child = obj
