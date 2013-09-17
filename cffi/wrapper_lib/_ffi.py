import cffi

ffi = cffi.FFI()
ffi.cdef("""
void free(void*);

void (*wrapper_lib_adjust_refcount)(void *, int);
""")

clib = ffi.verify("""
#include <stdlib.h>

void (*wrapper_lib_adjust_refcount)(void *, int);
""")
