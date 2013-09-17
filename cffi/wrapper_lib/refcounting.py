from _ffi import ffi, clib

refcounts = { }

@ffi.callback('void(*)(void*, int)')
def adjust_refcount(handle, offset):
    obj = ffi.from_handle(handle)
    if obj in refcounts:
        refcounts[obj][0] -= offset

        if refcounts[obj][0] <= 0:
            del refcounts[obj]
    else:
        assert offset > 0
        refcounts[obj] = (offset, handle)

def get_refcounted_handle(obj):
    if obj in refcounts:
        return refcounts[obj][1]
    else:
        return ffi.new_handle(obj)

clib.wrapper_lib_adjust_refcount = adjust_refcount
