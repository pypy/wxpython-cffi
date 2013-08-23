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
