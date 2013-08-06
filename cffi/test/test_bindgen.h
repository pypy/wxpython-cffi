int simple_global_func();
float global_func_with_args(int i, double j);
double custom_code_global_func();

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

private:
    int m_i;
};
