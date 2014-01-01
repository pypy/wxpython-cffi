#include <ctime>
#include <string>
using std::string;

#define prefixedSOME_INT 15

typedef int IntAlias;

extern const char *global_str;
extern const char *other_global_str;


int simple_global_func();
float global_func_with_args(int i, double j);
double custom_code_global_func();

int overloaded_func();
double overloaded_func(double i);

int std_string_len(string *str);
int std_string_len(string *str, int len);

int get_coords(int *x, int *y);
int get_coords_ref(int &x, int &y);

void get_mappedtype(string *x, string **y);
void get_mappedtype_ref(string &x, string *&y);

void give_me_the_time(time_t);
void give_me_the_time(double);

enum BOOLEAN
{
    BOOL_TRUE = -1,
    BOOL_FALSE = -2
};

class SimpleClass
{
public:
    int simple_method(double f);
};

class SimpleSubclass : public SimpleClass
{ };

struct IntWrapper
{
    IntWrapper(int i_=0) : i(i_) { }
    int i;
};

int global_func_with_default(const char *str, const IntWrapper &i);

class VMethClass
{
public:
    virtual ~VMethClass() { }
    virtual int virtual_method(int i);
    int call_virtual(int i);

    virtual int overridden_vmeth1();
    int call_overridden_vmeth1();

    virtual VMethClass* overridden_vmeth2();
    VMethClass* call_overridden_vmeth2();

    virtual IntWrapper overridden_vmeth3(int i);
    IntWrapper call_overridden_vmeth3(int i);

    virtual int unoverridden_cppvmeth(int i);
    int call_unoverridden_cppvmeth(int i);

};

class VMethSubclass : public VMethClass
{
public:
    virtual int overridden_vmeth1();
    virtual VMethSubclass* overridden_vmeth2();
    virtual IntWrapper overridden_vmeth3(int i);
};

class PMethClass
{
protected:
    char protected_method(char c);
    static int static_protected_method() { return -2; }
};

class VDtorClass
{
public:
    virtual ~VDtorClass() { };

    void delete_self()
    {
        delete this;
    }
};

class VDtorSubclass : public VDtorClass
{};

class VDtorSubSubclass : public VDtorSubclass
{};

class PVMethClass
{
protected:
    virtual int protected_virtual_method(int i);

public:
    virtual ~PVMethClass() { }
    int call_method(int i);
};

class CtorsClass
{
public:
    CtorsClass() : m_i(0) {};
    CtorsClass(const CtorsClass &other) : m_i(other.m_i) {};
    CtorsClass(int i) : m_i(i) {};

    int get();

protected:
    void set(int i);

private:
    int m_i;
};

extern CtorsClass global_wrapped_obj;

void get_wrappedtype(CtorsClass *x, CtorsClass **y);
void get_wrappedtype_ref(CtorsClass &x, CtorsClass *&y);

class PrivateCopyCtorClass
{
public:
    PrivateCopyCtorClass() { }

private:
    PrivateCopyCtorClass(const PrivateCopyCtorClass&) { }
};

class PrivateCopyCtorSubclass : public PrivateCopyCtorClass
{ };

class PCtorClass
{
protected:
    PCtorClass(int i) : m_i(i) { };

public:
    int get();

private:
    int m_i;
};

class ReturnWrapperClass
{
public:
    ReturnWrapperClass(int i) : m_i(i) {};
    static ReturnWrapperClass new_by_value(int i);
    static ReturnWrapperClass* new_by_ptr(int i);
    static ReturnWrapperClass& new_by_ref(int i);
    static const ReturnWrapperClass& new_by_cref(int i);
    static const ReturnWrapperClass& new_by_nocopy_cref(int i);

    ReturnWrapperClass self_by_value();
    ReturnWrapperClass* self_by_ptr();
    ReturnWrapperClass& self_by_ref();
    const ReturnWrapperClass& self_by_cref();
    const ReturnWrapperClass& self_by_nocopy_cref();

    int get();

private:
    int m_i;

};

class PrivateCCtorReturnWrapperClass
{
public:
    PrivateCCtorReturnWrapperClass(int i) : m_i(i) {};

    static const PrivateCCtorReturnWrapperClass& new_by_cref(int i);

    const PrivateCCtorReturnWrapperClass& self_by_cref();

    int get()
    {
        return m_i;
    }

private:
    PrivateCCtorReturnWrapperClass(const ReturnWrapperClass&);

    int m_i;
};

class MemberVarClass
{
public:
    MemberVarClass(int i) : m_i(i) {}


    int Get_i();
    void Set_i(int i);

    int m_i;
};

class NestedClassesOuter
{
public:
    class NestedClassesInner
    {
    public:
        virtual ~NestedClassesInner() { }
        virtual int vmeth();
        int call_vmeth();

        int m_i;
        int Get_i();
        void Set_i(int i);

        void overloaded();
        void overloaded(double f);
    };

    class NestedClassesInnerVirtual
    {
    public:
        virtual ~NestedClassesInnerVirtual() { }
        NestedClassesInnerVirtual* make()
        {
            return new NestedClassesInnerVirtual();
        }
    };
};

class NestedClassReturnDependant
{
public:
    NestedClassesOuter::NestedClassesInner get();
};

class NestedClassArgDependant
{
public:
    int get(const NestedClassesOuter::NestedClassesInner &i);
};

class ClassWithEnum
{
public:
    enum BOOLEAN
    {
        BOOL_TRUE = -10,
        BOOL_FALSE = -20
    };

    BOOLEAN flip(BOOLEAN b)
    {
        if(b == BOOL_TRUE)
            return BOOL_FALSE;
        return BOOL_TRUE;
    }
};

class DefaultsClass
{
public:
    enum DefaultsEnum
    {
        Defaults_A,
        Defaults_B,
    };
    int defaults_method(DefaultsEnum f = Defaults_A)
    {
        return f;
    }
};

class OperatorsClass
{
public:
    int x, y;

    OperatorsClass(int x_, int y_) : x(x_), y(y_) {};
    OperatorsClass& operator+=(const OperatorsClass &rhs);
    OperatorsClass& operator-=(const OperatorsClass &rhs);
};

class PyIntClass
{
public:
    char noPyInt(char c) { return c; };
    char onReturn(char c) { return c; };
    char onParameter(char c) { return c; };
    char onBoth(char c) { return c; };

    char overloaded() { return 'c'; }
    char overloaded(char c) { return c; }
};

struct Vector;
class ArrayClass
{
public:
    virtual ~ArrayClass() { }
    ArrayClass() : m_i(0) {}
    ArrayClass(int i) : m_i(i) {}
    int m_i;

    static int sum(ArrayClass *objs, int len);
    static int sum_mapped_type(Vector *objs, int len);
    virtual int sum_virt(ArrayClass *objs, int len);
    int call_sum_virt(ArrayClass *objs, int len);
};

class MappedTypeClass
{
public:
    virtual ~MappedTypeClass() { }
    string m_name;
    virtual string get_name();
    string call_get_name();

    virtual string concat(string *s, int len);
    string call_concat(string *s, int len);
};

class WrappedTypeClass
{
public:
    virtual ~WrappedTypeClass() { }
    virtual CtorsClass & get_ref();
    CtorsClass & call_get_ref();

    virtual CtorsClass * get_ptr();
    CtorsClass * call_get_ptr();

    virtual CtorsClass get_value();
    CtorsClass call_get_value();
};

struct Vector
{
    Vector() { }
    Vector(int i_, int j_) : i(i_), j(j_) { }
    int i;
    int j;
};

class IntWrapperClass
{
public:
    virtual ~IntWrapperClass() { }
    virtual IntWrapper trivial_mappedtype(IntWrapper i, IntWrapper &k);
    IntWrapper call_trivial_mappedtype(IntWrapper i, IntWrapper &k);

    virtual IntWrapper trivial_inout_mappedtype(IntWrapper i, IntWrapper &k);
    IntWrapper call_trivial_inout_mappedtype(IntWrapper i, IntWrapper &k);
};

class OutClass
{
public:
    virtual ~OutClass() { }
    virtual int get_coords_ptr(int *x, int *y);
    virtual int get_coords_ref(int &x, int &y);
    virtual void get_mappedtype_ptr(string *x, string **y);
    virtual void get_mappedtype_ref(string &x, string *&y);
    virtual void get_wrappedtype_ptr(CtorsClass *x, CtorsClass **y);
    virtual void get_wrappedtype_ref(CtorsClass &x, CtorsClass *&y);

    int call_get_coords_ptr(int *x, int *y);
    int call_get_coords_ref(int &x, int &y);
    void call_get_mappedtype_ptr(string *x, string **y);
    void call_get_mappedtype_ref(string &x, string *&y);
    void call_get_wrappedtype_ptr(CtorsClass *x, CtorsClass **y);
    void call_get_wrappedtype_ref(CtorsClass &x, CtorsClass *&y);
};

class InOutClass
{
public:
    virtual ~InOutClass() { }
    virtual void double_ptr(int *i);
    virtual void double_ref(int &i);

    virtual void double_ptr(CtorsClass *i);
    virtual void double_ref(CtorsClass &i);
    virtual void double_refptr(CtorsClass *&i);
    virtual void double_ptrptr(CtorsClass **i);

    virtual void double_ptr(Vector *i);
    virtual void double_ref(Vector &i);
    virtual void double_refptr(Vector *&i);
    virtual void double_ptrptr(Vector **i);

    void call_double_ptr(int *i);
    void call_double_ref(int &i);

    void call_double_ptr(CtorsClass *i);
    void call_double_ref(CtorsClass &i);
    void call_double_refptr(CtorsClass *&i);
    void call_double_ptrptr(CtorsClass **i);

    void call_double_ptr(Vector *i);
    void call_double_ref(Vector &i);
    void call_double_refptr(Vector *&i);
    void call_double_ptrptr(Vector **i);
};

class AbstractClass
{
public:
    virtual ~AbstractClass() { }
    virtual void purevirtual()=0;
};

class ConcreteSubclass : public AbstractClass
{
public:
    virtual void purevirtual() { }
};

class PureVirtualClass
{
public:
    virtual ~PureVirtualClass() { }
    virtual int purevirtual()=0;
    int call_purevirtual() { return purevirtual(); }
};

class SmartVector
{
public:
    SmartVector(int x_=0, int y_=0) : x(x_), y(y_) { }
    int x, y;
};

SmartVector double_vector(SmartVector &vec);
Vector double_mapped_vector(Vector &vec);

#define AllowNoneSmartVector SmartVector

class AllowNoneClass
{
public:
    long get_addr_ptr(SmartVector *v);
    long get_addr_ref(SmartVector &v);

    long allow_none_get_addr_ptr(SmartVector *v) { return get_addr_ptr(v); }
    long allow_none_get_addr_ref(SmartVector &v) { return get_addr_ref(v); }
};

class KeepReferenceClass
{
public:
    void keep_ref(KeepReferenceClass &i) { }
    void keep_ref2(KeepReferenceClass &i) { }
};

void global_keep_ref(KeepReferenceClass &i);

class TransferClass
{
public:
    TransferClass() { }
    TransferClass(int i) { }
    TransferClass(TransferClass * i) { }

    void transfer_param(TransferClass *obj) { }
    TransferClass *transfer_return(TransferClass *obj);
    void transferback_param(TransferClass *obj) { }
    TransferClass *transferback_return(TransferClass *obj);
    void transferthis_param(TransferClass * i) { }
    void transferthis_return() { }

    void transfer_array(TransferClass *&objs, int count)
    {
        delete[] objs;
        //Change the value of the pointer so if the code try to delete again it
        //sefault
        objs = (TransferClass*)-1;
    }
    void transfer_array(Vector *&objs, int count)
    {
        delete[] objs;
        objs = (Vector*)-1;
    }

    static void static_transfer_param(TransferClass *obj) { }
    static void static_transferback_param(TransferClass *obj) { }
    static TransferClass * static_transferback_return(TransferClass *obj)
    {
        return obj;
    }
};

void global_transfer_param(TransferClass *obj);
void global_transferback_param(TransferClass *obj);
TransferClass * global_transferback_return(TransferClass *obj);

class FactoryClass
{
public:
    virtual ~FactoryClass() { }
    virtual FactoryClass * make();
    FactoryClass * make_keep_ref(FactoryClass *ref);
    FactoryClass * make_transfer_this(FactoryClass *ref);

    FactoryClass * call_make();
};

class VirtualParametersOwnershipClass
{
public:
    virtual ~VirtualParametersOwnershipClass() { }
    virtual void by_value(CtorsClass v) { }
    virtual void by_ptr(CtorsClass *v) { }
    virtual void by_ref(CtorsClass &v) { }
    virtual void by_cref(const CtorsClass &v) { }
    virtual void by_cref_private_cctor(const PrivateCopyCtorClass &v) { }

    void call_by_value();
    void call_by_ptr();
    void call_by_ref();
    void call_by_cref();
    void call_by_cref_private_cctor();

};

class DeprecatedClass
{
public:
    void deprecated_method() { }
};

void deprecated_func();

class ExternalModuleSubclass : public SimpleClass
{
};

class VirtualCatcherBase
{
public:
    virtual ~VirtualCatcherBase() { }
    virtual const char *vmeth() { return ""; }
    const char *call_vmeth() { return vmeth(); }
};

class DetectableBase
{
public:
    virtual ~DetectableBase() { }
    virtual const char * get_class_name() { return "DetectableBase"; }
};

class DetectableSubclass : public DetectableBase
{
public:
    virtual const char * get_class_name() { return "DetectableSubclass"; }
};

DetectableBase * get_detectable_object(bool base);

class VoidPtrClass
{
public:
    virtual ~VoidPtrClass() { }
    virtual void* copy_data(void *data, int size);
    void* call_copy_data(void *data, int size);
};

struct OpaqueType
{
    int i;
};

OpaqueType* make_opaque_object(int i);
int take_opaque_object(OpaqueType*);

class DocstringClass
{
public:
    void docstring_meth() { }
    void docstring_overloaded_meth() { }
    void docstring_overloaded_meth(int i) { }
};

typedef CtorsClass CtorsAlias;
class TypedefClass
{
public:
    CtorsAlias& passthrough(CtorsAlias &obj) { return obj; }
};

class CustomCppMethodsClass
{
public:
    virtual ~CustomCppMethodsClass() { }
    int basic_method() { return -42; }

    void custom_pycode_only(int *data)
    {
        data[0] = data[0] + data[1];
    }

    virtual int custom_pycode_and_cppcode(int(*cb)(int))
    {
        return cb(11) * -2;
    }

    int call_custom_pycode_and_cppcode(int(*cb)(int))
    {
        return this->custom_pycode_and_cppcode(cb);
    }
};

typedef char CharTypedef;

class CharTypesClass
{
public:
    int char_scalar(char c)
    {
        return c;
    }

    int schar_scalar(signed char c)
    {
        return c;
    }

    int uchar_scalar(unsigned char c)
    {
        return c;
    }

    int char_vector(char *c)
    {
        return c[0];
    }

    int schar_vector(signed char *c)
    {
        return c[0];
    }

    int uchar_vector(unsigned char *c)
    {
        return c[0];
    }

    wchar_t * wchar_string(wchar_t *c)
    {
        wchar_t *cpy = (wchar_t*)malloc(sizeof(wchar_t) * wcslen(c));
        wcscpy(cpy, c);
        return cpy;
    }

    CharTypedef * typedef_string(CharTypedef *c)
    {
        char *cpy = (char*)malloc(sizeof(char) * strlen(c));
        strcpy(cpy, c);
        return cpy;
    }
};

class UnsignedTypesClass
{
public:
    unsigned u(unsigned i)
    {
        return -i;
    }

    unsigned int ui(unsigned int i)
    {
        return -i;
    }

    unsigned long long ull(unsigned long long i)
    {
        return -i;
    }
};

class NestedTypedefsClass
{
public:
    typedef int int1;
    typedef int1 int2;
    int2 return_typedef(int2 i)
    {
        return i - 2;
    }
};
