#define prefixedSOME_INT 15

extern const char *global_str;

int simple_global_func();
float global_func_with_args(int i, double j);
double custom_code_global_func();

int overloaded_func();
double overloaded_func(double i);

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
