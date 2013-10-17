#include <cstring>
#include <cstdlib>

extern "C"
{
    void (*WL_ADJUST_REFCOUNT)(void *, int);
    char **WL_EXCEPTION_NAME;
    char **WL_EXCEPTION_STRING;
}

#define WL_SET_EXCEPTION(name, string)\
    do\
    {\
        *WL_EXCEPTION_NAME = (char*)malloc(strlen(name)+1);\
        strcpy(*WL_EXCEPTION_NAME, name);\
        *WL_EXCEPTION_STRING = (char*)malloc(strlen(string)+1);\
        strcpy(*WL_EXCEPTION_STRING, string);\
    } while(0);

#define WL_CHECK_EXCEPTION()\
    (*WL_EXCEPTION_NAME != NULL)

#ifdef __GNUC__
#    define WL_INTERNAL extern "C" __attribute__((visibility ("internal")))
#else
#    define WL_INTERNAL extern "C"
#endif

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
        WL_ADJUST_REFCOUNT(handle, 1);
    }

    cffiRefCountedPyObjBase(const cffiRefCountedPyObjBase &other)
      : m_handle(other.m_handle)
    {
        WL_ADJUST_REFCOUNT(other.m_handle, 1);
    }

    ~cffiRefCountedPyObjBase()
    {
        WL_ADJUST_REFCOUNT(m_handle, -1);
    }

    void *get_handle()
    {
        return m_handle;
    }

protected:
    void *m_handle;
};
