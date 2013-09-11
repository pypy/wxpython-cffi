#include <cstring>
#include <cstdlib>

#define CFFI_SET_EXCEPTION(name, string)\
    do\
    {\
        cffiexception_name = (char*)malloc(strlen(name));\
        strcpy(cffiexception_name, name);\
        cffiexception_string = (char*)malloc(strlen(string));\
        strcpy(cffiexception_string, string);\
    } while(0);

template<typename T, typename CType>
struct cfficonvert_mappedtype
{
    static CType cpp2c(T *cpp_obj);
    static inline CType cpp2c(T &cpp_obj)
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
