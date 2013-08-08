#include <ctype.h>
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

char PMethClass::protected_method(char c)
{
    return toupper(c);
}

int CtorsClass::get()
{
    return m_i;
}

void CtorsClass::set(int i)
{
    m_i = i;
}

ReturnWrapperClass ReturnWrapperClass::new_by_value(int i)
{
    return ReturnWrapperClass(i);
}

ReturnWrapperClass* ReturnWrapperClass::new_by_ptr(int i)
{
    return new ReturnWrapperClass(i);
}

ReturnWrapperClass& ReturnWrapperClass::new_by_ref(int i)
{
    return *(new ReturnWrapperClass(i));
}

const ReturnWrapperClass& ReturnWrapperClass::new_by_cref(int i)
{
    return *(new ReturnWrapperClass(i));
}

ReturnWrapperClass ReturnWrapperClass::self_by_value()
{
    return *this;
}

ReturnWrapperClass* ReturnWrapperClass::self_by_ptr()
{
    return this;
}

ReturnWrapperClass& ReturnWrapperClass::self_by_ref()
{
    return *this;
}

const ReturnWrapperClass& ReturnWrapperClass::self_by_cref()
{
    return *this;
}

int ReturnWrapperClass::get()
{
    return m_i;
}
