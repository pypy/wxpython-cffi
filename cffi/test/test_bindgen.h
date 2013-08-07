#define prefixedSOME_INT 15

int simple_global_func();
float global_func_with_args(int i, double j);
double custom_code_global_func();

int overloaded_func();
double overloaded_func(double i);

class SimpleClass
{
public:
    int simple_method(double f);
};

class VMethClass
{
public:
    virtual int virtual_method(int i);
    int call_virtual(int i);
};

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

class ReturnWrapperClass
{
public:
    ReturnWrapperClass(int i) : m_i(i) {};
    static ReturnWrapperClass new_by_value(int i);
    static ReturnWrapperClass* new_by_ptr(int i);
    static ReturnWrapperClass& new_by_ref(int i);

    int get();

private:
    int m_i;

};
