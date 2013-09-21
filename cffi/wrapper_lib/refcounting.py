import contextlib

from _ffi import ffi, clib

refcounts = { }


def adjust_refcount(handle, offset):
    obj = ffi.from_handle(handle)
    obj_id = id(obj)
    if obj_id in refcounts:
        refcounts[obj_id][0] += offset

        if refcounts[obj_id][0] <= 0:
            del refcounts[obj_id]
    else:
        assert offset > 0
        refcounts[obj_id] = [offset, handle, obj]

@contextlib.contextmanager
def get_refcounted_handle(obj):
    """
    Create or get an existing handle for ``obj`` and temporarily increment
    its refcount, ensuring that the handle being refcounted has ownerhsip.

    This is useful for when passing a handle to a C fuction that will then
    increment the ref count. If the handle were created with just
    ffi.new_handle, the cdata that adjust_refcount receives (from being called
    by the C function) will be non-owning. Thus, when the original handle goes
    out of scope, the refcounted mapping would become invalid.
    """
    obj_id = id(obj)
    if obj_id in refcounts:
        handle = refcounts[obj_id][1]
    else:
        handle = ffi.new_handle(obj)
    adjust_refcount(handle, 1)
    yield handle
    adjust_refcount(handle, -1)

# Its important that the callback is created this way rather than via a
# decorator on adjust_refcount. If a decorator were used, whenever
# adjust_refcount would be called from Python, it would receive a copy of the
# handle instead of the handle itself. Only the original handle keeps the
# association alive, so the association would die almost immediately.
adjust_refcount_cb = ffi.callback('void(*)(void*, int)')(adjust_refcount)
clib.wrapper_lib_adjust_refcount = adjust_refcount_cb
