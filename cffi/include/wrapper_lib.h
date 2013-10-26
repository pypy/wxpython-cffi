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
struct WL_mappedtype
{
    static CType to_c(T *cpp_obj);
    static CType to_c(const T *cpp_obj)
    {
        return to_c(const_cast<T *>(cpp_obj));
    }
    static inline CType to_c(const T &cpp_obj)
    {
        return to_c(&cpp_obj);
    }

    static T* to_cpp(CType cdata);

    static T* to_cpp_array(CType *cdata, int count)
    {
        T * array = new T[count];
        for(int i = 0; i < count; i++)
        {
            T *tmp = to_cpp(cdata[i]);
            array[i] = *tmp;
            delete tmp;
        }
        return array;
    }

    static CType* to_c_array(T *objs, int count)
    {
        CType * array = (CType*)malloc(sizeof(CType) * count);
        for(int i = 0; i < count; i++)
            array[i] = to_c(objs[i]);
        return array;
    }
};


template<typename T>
T* WL_wrappedtype_array_to_cpp(T **objs, int count)
{
    T * array = new T[count];
    for(int i = 0; i < count; i++)
        array[i] = *objs[i];
    return array;
}

template<typename T>
T** WL_wrappedtype_array_to_c(T *objs, int count)
{
    T **array = (T**)malloc(sizeof(T*) * count);
    for(int i = 0; i < count; i++)
        array[i] = objs + i;
    return array;
}

template<typename T>
class WL_RefCountedPyObjBase : public T
{
public:
    WL_RefCountedPyObjBase(void *handle)
      : m_handle(handle)
    {
        WL_ADJUST_REFCOUNT(handle, 1);
    }

    WL_RefCountedPyObjBase(const WL_RefCountedPyObjBase &other)
      : m_handle(other.m_handle)
    {
        WL_ADJUST_REFCOUNT(other.m_handle, 1);
    }

    ~WL_RefCountedPyObjBase()
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
