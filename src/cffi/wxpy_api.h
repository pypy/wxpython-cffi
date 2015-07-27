#ifndef INCLUDE_GUARD__cffi_wxpy_api_H
#define INCLUDE_GUARD__cffi_wxpy_api_H
// Redefine some of the marcos used to set exceptions in sip backend to make
// porting to the cffi backend easier

#define wxPyErr_SetString WL_SET_EXCEPTION
#define PyErr_SetString WL_SET_EXCEPTION
#define PyErr_NoMemory() WL_SET_EXCEPTION(PyExc_MemoryError, "")

#define PyErr_Occurred() WL_CHECK_EXCEPTION()

#define wxPyRaiseNotImplemented() WL_SET_EXCEPTION("NotImplemented", "")
#define wxPyRaiseNotImplementedMsg(msg) WL_SET_EXCEPTION("NotImplemented", msg)

// Redefine CPython's exception names so we can reuse them
#define PyExc_ValueError "ValueError"
#define PyExc_TypeError "TypeError"
#define PyExc_MemoryError "MemoryError"
#define PyExc_RuntimeError "RuntimeError"
#define PyExc_StopIteration "StopIteration"
#define PyExc_IndexError "IndexError"
#define PyExc_SystemExit "SystemExit"
#define PyExc_SystemError "SystemError"
#define wxAssertionError "wxAssertionError"

typedef void* wxPyThreadBlocker;

typedef ssize_t Py_ssize_t;
typedef ssize_t SIP_SSIZE_T;
typedef unsigned char  byte;
typedef unsigned char* buffer;

#endif  /* INCLUDE_GUARD */
