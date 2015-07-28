import weakref
import collections

from _ffi import ffi, clib


class WrapperType(type):
    """
    Metaclass for CppWrapper.

    The primary purpose of this metaclass is to automate the handling of
    virtual methods on subclasses of CppWrapper.
    """
    def __init__(self, name, bases, attrs):
        if '_vtable' in attrs:
            # If the class has a _vtable attribute, then (we'll assume) it is
            # a wrapper for a C++ class that has virtual methods. Thus we need
            # to populate the vtable with the dispatcher callbacks
            self._vdata = VData(ffi, self._vtable, self._set_vflag,
                                self._set_vflags, True)

            for name, attr in attrs.iteritems():
                if isinstance(attr, VirtualDispatcher):
                    self._vtable[attr.index] = ffi.cast('void*', attr.func)
                    self._vdata.dispatchers.append(attr)
                    delattr(self, name)
            del self._vtable
            del self._set_vflag
            del self._set_vflags

            self._vmeths = {}
            for name, attr in attrs.iteritems():
                if isinstance(attr, VirtualMethod):
                   attr.name = name
            return

        # If the class has no _vtable, then it is a subclass of a wrapper or a
        # wrapper for a C++ that has no virtual methods
        for base in self.mro():
            if '_vdata' in base.__dict__ and base._vdata.direct_wrapper:
                base_wrapper = base
                break
        else:
            # None of the base classes have virtual methods, so we're done
            return

        # Getting here means this is a subclass of a wrapper with virtual
        # methods. We'll build an array that will serve as the default value
        # for the virtual override flags for instances of this subclass.
        self._vdata = VData(ffi, self._vdata.vtable, self._vdata.set_vflag,
                            self._vdata.set_vflags, False)

        # Automatically set the default vflag for the classes Dtor, if it has
        # a virtual Dtor
        for dispatcher in base_wrapper._vdata.dispatchers:
            if dispatcher.func is global_dtor:
                self._vdata.default_vflags[dispatcher.index] = 1
                break

        # Note this loop will only catch VirtualMethods declared directly on
        # base_wrapper. We don't actually want any declared on base_wrapper's
        # superclass(es).
        for name, attr in base_wrapper.__dict__.iteritems():
            if isinstance(attr, VirtualMethod):
                if getattr(self, name).__func__ is not attr.func:
                    # Set the default flag if the method is not the same as the
                    # original one in the base wrapper
                    for i in attr.indices:
                        self._vdata.default_vflags[i] = 1
                else:
                    # Make a duplicate of the VirtualMethod object so when its
                    # func attribute is changed in __get__ it only affects this
                    # class
                    vmeth = VirtualMethod()(attr)
                    vmeth.name = name
                    setattr(self, name, vmeth)

    def __setattr__(self, name, value):
        attr = self.__dict__.get(name, None)
        if isinstance(attr, VirtualMethod):
            attr.func = value
            for i in attr.indices:
                self._vdata.default_vflags[i] = 1
            for obj in self._vdata.instances:
                for i in attr.indices:
                    obj._vdata.set_vflag(obj, i)
        else:
            super(WrapperType, self).__setattr__(name, value)

class VData(object):
    def __init__(self, ffi, vtable, set_vflag, set_vflags, direct_wrapper):
        self.vtable = vtable
        self.default_vflags = ffi.new('unsigned char[]', len(vtable))
        self.set_vflag = set_vflag
        self.set_vflags = set_vflags
        self.instances = weakref.WeakSet()
        self.dispatchers = []
        self.direct_wrapper = direct_wrapper

class CastData(object):
    def get_offset_ptr(self, ptr, cls):
        try:
            return ptr + self.offsets[cls]
        except KeyError:
            # 0 offsets aren't stored, so when the lookup fails, assume the
            # pointer the same for the conversion (ie do no error handling.)
            return ptr
        except AttributeError:
            self.setup_offsets_table(ptr)
            return self.get_offset_ptr(ptr, cls)

    def get_offsets_table(self, ptr):
        try:
            return self.offsets
        except AttributeError:
            self.setup_offsets_table(ptr)
            return self.offsets

    def setup_offsets_table(self, ptr):
        # Setup of the offsets table is delayed until we have an instance.
        # Technically, casting with a dummy pointer is possible, but is
        # undefined behavior. This should be slightly safer and gives us a path
        # to potentially support virtual inhertiance at a later date.
        self.offsets = { }
        for base, cast_func in self.castfuncs:
            casted_ptr = cast_func(ptr)

            offset = casted_ptr - ptr
            if offset != 0:
                # Only store non-0 offsets. Unstored offsets are assume 0.
                self.offsets[base] = offset
                # Copy the offsets to each base's base, adding the offset
                for (base_base, base_offset) in \
                    base._castdata.get_offsets_table(ptr).iteritems():
                    self.offsets[base_base] = base_offset + offset
            else:
                # Copy the offsets to each base's base
                self.offsets.update(base._castdata.get_offsets_table(ptr))

    def __init__(self, castfuncs):
        self.castfuncs = castfuncs

class VirtualMethod(object):
    """
    Descriptor for virtual methods. Automatically handles updating the vflag on
    on an object when the method is changed. Should be used as a decorator and
    can be stacked to allow one method to handle multiple overloads.
    """
    def __init__(self, *args):
        self.indices = list(args)

    def __call__(self, func):
        if isinstance(func, VirtualMethod):
            # Allow @VirtualMethod(n) decorators to be stacked
            self.indices.extend(func.indices)
            self.func = func.func
            return self
        self.func = func
        return self

    def __get__(self, obj, cls):
        if obj is not None and self.name in obj._vmeths:
            return obj._vmeths[self.name]
        else:
            return self.func.__get__(obj, cls)

    def __set__(self, obj, value):
        if '_vmeths' not in obj.__dict__:
            obj._vmeths = {}
        obj._vmeths[self.name] = value
        if obj._py_created:
            # We can only guarantee that it's safe to try setting vflags if
            # Python create the object
            for i in self.indices:
                obj._vdata.set_vflag(obj, i)

    def __repr__(self):
        return '<VirtualMethod%s: %s>' % (self.indices,
                                            repr(getattr(self, 'func', None)))

class VirtualMethodStub(VirtualMethod):
    """
    A way to inherit virtual methods without duplicating the code for them.
    This necessary because the vtable index of a virtual method may be
    different on the super- and sub-classes. (And infact must be different in
    the case of multiple inheritance.)
    """
    def __init__(self, vmeth, *args):
        super(VirtualMethodStub, self).__init__(*args)
        self.func = getattr(vmeth, '__func__', vmeth)

class VirtualDispatcher(object):
    def __init__(self, index):
        self.index = index

    def __call__(self, func):
        if func is None:
            func = global_dtor
        self.func = func
        return self

    def __repr__(self):
        return '<VirtualDispatcher: %s>' % repr(getattr(self, 'func', None))

class CppWrapper(object):
    __metaclass__ = WrapperType

    def __init__(self, cpp_obj, py_owned=True, py_created=True,
                 external_ref=False):
        self._cpp_obj = cpp_obj if cpp_obj is not None else ffi.NULL
        self._py_owned = py_owned
        self._py_created = py_created
        remember_ptr(self, self._cpp_obj, external_ref)

        self._parent = None
        self._child = None
        self._next_sibling = None
        self._prev_sibling = None

        if hasattr(self, '_vdata') and self._py_created:
            # See comment about about setting vflags and _py_created
            self._vdata.set_vflags(self, self._vdata.default_vflags)
            self._vdata.instances.add(self)

    def __del__(self):
        # We have to check forget_ptr because it may be garbage collected by
        # the time this is called
        if not self._py_owned and forget_ptr is not None:
            forget_ptr(self._cpp_obj)

    @classmethod
    def _from_ptr(cls, ptr, py_owned=False, external_ref=False):
        obj = CppWrapper.__new__(cls, _override_abstract_class=True)
        CppWrapper.__init__(obj, ptr, py_owned, False, external_ref)
        return obj


def init_wrapper(obj, ptr, is_subclass):
    CppWrapper.__init__(obj, ptr, py_created=is_subclass)

def hassubclass(cls):
    return hasattr(cls, '_vdata')


@ffi.callback('void(*)(void*)')
def global_dtor(ptr):
    # TODO: set the wrapper object's ptr to NULL and add checks to prevent
    #       calls to objects that have been deleted.
    if not ptr in object_map:
        # TODO: raise an exception? This is called via a cffi callback, so the
        #       exception wouldn't propagate to regular python code
        return
    else:
        # Clear the wrapper object's pointer so it we don't try calling methods
        # on a deleted object.
        object_map[ptr]._cpp_obj = ffi.NULL

    forget_ptr(ptr)


cpp_owned_objects = set()
object_map = weakref.WeakValueDictionary()

classname_registry = { }

def register_cpp_classname(cppname, subclass):
    assert issubclass(subclass, CppWrapper)
    classname_registry[cppname] = subclass

def obj_from_ptr(ptr, klass=CppWrapper, is_new=False):
    if ptr == ffi.NULL:
        return None
    if hasattr(klass, '_get_cpp_classname_'):
        str_ptr = klass._get_cpp_classname_(ptr)
        classname = ffi.string(str_ptr)
        clib.free(str_ptr)

        klass = classname_registry.get(classname, klass)
    if object_map is None or ptr not in object_map:
        # If an python object for this pointer doesn't yet exist, create one
        obj = klass._from_ptr(ptr, is_new)
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
    obj = klass._from_ptr(ptr, is_new)

    if old_parent is not None:
        _detach_from_parent(obj)
        object_map[ptr] = obj
        _attach_to_parent(obj, old_parent())
    else:
        object_map[ptr] = obj
    return obj

def get_ptr(obj, cls=None):
    if obj is None:
        return ffi.NULL

    if isinstance(obj, CppWrapper):
        return obj._castdata.get_offset_ptr(obj._cpp_obj, cls)

    raise TypeError('obj is not a wrapper for a C++ object')

def remember_ptr(obj, ptr, external_ref=False):
    if obj is None:
        return
    if external_ref:
        # In some (one) situtations, obj needs to be kept alive even if it
        # stops being referenced by Python.
        cpp_owned_objects.add(obj)
    object_map[ptr] = obj
    for basecls, offset in obj._castdata.get_offsets_table(ptr).items():
        if getattr(basecls, '_vdata', None):
            object_map[ptr + offset] = obj

def forget_ptr(ptr):
    if ptr in object_map:
        obj = object_map[ptr]
        cpp_owned_objects.discard(obj)
        del object_map[ptr]

        for basecls, offset in obj._castdata.get_offsets_table(ptr).items():
            if getattr(basecls, '_vdata', None):
                del object_map[ptr + offset]

        _detach_children(obj)
        # TODO: does obj need to detach from its parent too?

def is_alive(obj):
    return bool(obj._cpp_obj)

def take_ownership(obj):
    if obj is None:
        return
    obj._py_owned = True
    cpp_owned_objects.discard(obj)
    _detach_from_parent(obj)

global_references = set()
def keep_reference(obj, key=None, owner=None):
    if obj is None:
        return
    if owner is None:
        # If this was called from a static method or global function, we need
        # to keep obj alive forever.
        global_references.add(obj)
        return

    if not hasattr(owner, '_extra_references'):
        owner._extra_references = {}
    owner._extra_references[key] = obj

def give_ownership(obj, parent=None, external_ref=False):
    if obj is None:
        return
    obj._py_owned = False

    _detach_from_parent(obj)
    if parent is not None:
        # If parent is not None, the parent will hold the reference that keeps
        # obj alive
        _attach_to_parent(obj, parent)
    elif external_ref:
        # If C++ is holding a reference to obj, keep it alive via
        # cpp_owned_objects. This will keep it alive until its ownership is
        # changed by Python or its (hopefully virtual) C++ Dtor is called
        cpp_owned_objects.add(obj)

def instancecheck(obj, cls):
    return isinstance(obj, cls) or (hasattr(cls, '_pyobject_mapping_') and
                                    isinstance(obj, cls._pyobject_mapping_))

def convert_to_type(obj, cls):
    if isinstance(obj, cls):
        return obj
    if (hasattr(cls, '_pyobject_mapping_') and
        isinstance(obj, cls._pyobject_mapping_)):
        return cls._pyobject_mapping_.convert(obj)
    return None

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


class MappedType(type):
    def __new__(cls, name, bases, attrs):
        if len(bases) == 1 and (bases[0] == object or bases[0] == MappedBase):
            return super(MappedType, cls).__new__(cls, name, bases, attrs)
        raise TypeError('mapped types may not be subclassed.')

    def __instancecheck__(self, instance):
        return self.__instancecheck__(instance)

class MappedBase(object):
    __metaclass__ = MappedType

    def __init__(self, *args, **kwargs):
        raise TypeError('mapped types may not be instantiated.')
