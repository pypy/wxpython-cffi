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
    virtual ~VDtorClass { };
};
