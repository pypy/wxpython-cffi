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

int SimpleClass::simple_method(double f)
{
    return f;
}
