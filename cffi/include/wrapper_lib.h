#include <cstring>
#include <cstdlib>

extern "C" void (*wrapper_lib_adjust_refcount)(void *, int);

#define CFFI_SET_EXCEPTION(name, string)\
    do\
    {\
        cffiexception_name = (char*)malloc(strlen(name)+1);\
        strcpy(cffiexception_name, name);\
        cffiexception_string = (char*)malloc(strlen(string)+1);\
        strcpy(cffiexception_string, string);\
    } while(0);

#define CFFI_CHECK_EXCEPTION()\
    (cffiexception_name != NULL)

template<typename T, typename CType>
struct cfficonvert_mappedtype
{
    static CType cpp2c(T *cpp_obj);
    static CType cpp2c(const T *cpp_obj)
    {
        return cpp2c(const_cast<T *>(cpp_obj));
    }
    static inline CType cpp2c(const T &cpp_obj)
    {
        return cpp2c(&cpp_obj);
    }

    static T* c2cpp(CType cdata);

    static T* c2cpp_array(CType *cdata, int count)
    {
        T * array = new T[count];
        for(int i = 0; i < count; i++)
        {
            T *tmp = c2cpp(cdata[i]);
            array[i] = *tmp;
            delete tmp;
        }
        return array;
    }

    static CType* cpp2c_array(T *objs, int count)
    {
        CType * array = (CType*)malloc(sizeof(CType) * count);
        for(int i = 0; i < count; i++)
            array[i] = cpp2c(objs[i]);
        return array;
    }
};


template<typename T>
T* cfficonvert_wrappedtype_c2cpp_array(T **objs, int count)
{
    T * array = new T[count];
    for(int i = 0; i < count; i++)
        array[i] = *objs[i];
    return array;
}

template<typename T>
T** cfficonvert_wrappedtype_cpp2c_array(T *objs, int count)
{
    T **array = (T**)malloc(sizeof(T*) * count);
    for(int i = 0; i < count; i++)
        array[i] = objs + i;
    return array;
}

template<typename T>
class cffiRefCountedPyObjBase : public T
{
public:
    cffiRefCountedPyObjBase(void *handle)
      : m_handle(handle)
    {
        wrapper_lib_adjust_refcount(handle, 1);
    }

    cffiRefCountedPyObjBase(const cffiRefCountedPyObjBase &other)
      : m_handle(other.m_handle)
    {
        wrapper_lib_adjust_refcount(other.m_handle, 1);
    }

    ~cffiRefCountedPyObjBase()
    {
        wrapper_lib_adjust_refcount(m_handle, -1);
    }

    void *get_handle()
    {
        return m_handle;
    }

protected:
    void *m_handle;
};
