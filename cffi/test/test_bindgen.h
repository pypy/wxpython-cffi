#include <string>
using std::string;

#define prefixedSOME_INT 15

extern const char *global_str;
extern const char *other_global_str;

int simple_global_func();
float global_func_with_args(int i, double j);
int global_func_with_default(const char *str);
double custom_code_global_func();

int overloaded_func();
double overloaded_func(double i);

int std_string_len(string *str);
int std_string_len(string *str, int len);

int get_coords(int *x, int *y);
int get_coords_ref(int &x, int &y);

void get_mappedtype(string *x, string **y);
void get_mappedtype_ref(string &x, string *&y);

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

class VMethClass
{
public:
    virtual int virtual_method(int i);
    int call_virtual(int i);
};

class VMethSubclass : public VMethClass
{ };

class PMethClass
{
protected:
    char protected_method(char c);
};

class VDtorClass
{
public:
    virtual ~VDtorClass() { };
};

class PVMethClass
{
protected:
    virtual int protected_virtual_method(int i);

public:
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

    ReturnWrapperClass self_by_value();
    ReturnWrapperClass* self_by_ptr();
    ReturnWrapperClass& self_by_ref();
    const ReturnWrapperClass& self_by_cref();
    const ReturnWrapperClass& self_by_nocopy_cref();

    int get();

private:
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
        virtual int vmeth();
        int call_vmeth();

        int m_i;
        int Get_i();
        void Set_i(int i);

        void overloaded();
        void overloaded(double f);
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

class ArrayClass
{
public:
    ArrayClass() : m_i(0) {}
    ArrayClass(int i) : m_i(i) {}
    int m_i;

    static int sum(ArrayClass *objs, int len);
    virtual int sum_virt(ArrayClass *objs, int len);
    int call_sum_virt(ArrayClass *objs, int len);
};

class MappedTypeClass
{
public:
    string m_name;
    virtual string get_name();
    string call_get_name();

    virtual string concat(string *s, int len);
    string call_concat(string *s, int len);
};

struct Vector
{
    Vector() { }
    Vector(int i_, int j_) : i(i_), j(j_) { }
    int i;
    int j;
};

struct IntWrapper
{
    IntWrapper(int i_=0) : i(i_) { }
    int i;
};

class IntWrapperClass
{
public:
    virtual IntWrapper trivial_mappedtype(IntWrapper i, IntWrapper &k);
    IntWrapper call_trivial_mappedtype(IntWrapper i, IntWrapper &k);

    virtual IntWrapper trivial_inout_mappedtype(IntWrapper i, IntWrapper &k);
    IntWrapper call_trivial_inout_mappedtype(IntWrapper i, IntWrapper &k);
};

class OutClass
{
public:
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
    virtual void double_ptr(int *i);
    virtual void double_ref(int &i);

    virtual void double_ptr(CtorsClass *i);
    virtual void double_ref(CtorsClass &i);

    virtual void double_ptr(Vector *i);
    virtual void double_ref(Vector &i);

    void call_double_ptr(int *i);
    void call_double_ref(int &i);

    void call_double_ptr(CtorsClass *i);
    void call_double_ref(CtorsClass &i);

    void call_double_ptr(Vector *i);
    void call_double_ref(Vector &i);
};

class AbstractClass
{
public:
    virtual void purevirtual()=0;
};

class ConcreteSubclass
{
public:
    virtual void purevirtual() { }
};

class PureVirtualClass
{
public:
    virtual int purevirtual()=0;
    int call_purevirtual() { return purevirtual(); }
};

class SmartVector
{
public:
    SmartVector(int x_, int y_) : x(x_), y(y_) { }
    int x, y;
};

SmartVector double_vector(SmartVector &vec);

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

    void transfer_param(TransferClass *obj) { }
    TransferClass *transfer_return(TransferClass *obj);
    void transferback_param(TransferClass *obj) { }
    TransferClass *transferback_return(TransferClass *obj);

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
