#ifndef WXPYBUFFER_H
#define WXPYBUFFER_H

struct wxPyBuffer
{
    size_t m_len;
    char *m_ptr;

    // Ensure that the buffer's size is the expected size.  Raises a 
    // Python ValueError exception and returns false if not.
    bool checkSize(size_t expectedSize) {
        if (m_len < expectedSize) {
            wxPyErr_SetString(PyExc_ValueError, "Invalid data buffer size.");
            return false;
        }
        return true;
    }

    // Make a simple C copy of the data buffer.  Malloc is used because 
    // the wxAPIs this is used with will later free() the pointer.  Raises 
    // a Python exception if there is an allocation error.
    void* copy() {
        void* ptr = malloc(m_len);
        if (ptr == NULL) {
            PyErr_NoMemory();
            return NULL;
        }            
        memcpy(ptr, m_ptr, m_len);
        return ptr;
    }
};
#endif
