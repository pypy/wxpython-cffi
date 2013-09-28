import cffi

ffi = cffi.FFI()
ffi.cdef("""
void free(void*);
""")

clib = ffi.verify("""
#include <stdlib.h>
""")
