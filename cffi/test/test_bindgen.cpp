/*
 * What do we need to test?
 *  - Simple global functions
 *  - Global functions with custom code
 *  - CppMethodDef global functions
 */

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
