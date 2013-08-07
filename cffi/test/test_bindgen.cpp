#include "test_bindgen.h"

int simple_global_func()
{
    return 10;
}

float global_func_with_args(int i, double j)
{
    return i * j;
}

double custom_code_global_func()
{
    return 2.0;
}

int overloaded_func()
{
    return 20;
}

double overloaded_func(double i)
{
    return i / 2;
}

int SimpleClass::simple_method(double f)
{
    return f;
}

int VMethClass::virtual_method(int i)
{
    return -i;
}

int VMethClass::call_virtual(int i)
{
    return this->virtual_method(i);
}

int CtorsClass::get()
{
    return m_i;
}
