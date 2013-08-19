#include <ctype.h>
#include <cstring>
#include "test_bindgen.h"

const char *global_str = "string";
const char *other_global_str = "other";
CtorsClass global_wrapped_obj(13);

int simple_global_func()
{
    return 10;
}

float global_func_with_args(int i, double j)
{
    return i * j;
}

int global_func_with_default(const char *str)
{
    return strlen(str);
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

int PVMethClass::protected_virtual_method(int i)
{
    return -i;
}

int PVMethClass::call_method(int i)
{
    return this->protected_virtual_method(i);
}

int CtorsClass::get()
{
    return m_i;
}

void CtorsClass::set(int i)
{
    m_i = i;
}

int PCtorClass::get()
{
    return m_i;
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

int MemberVarClass::Get_i()
{
    return m_i;
}

void MemberVarClass::Set_i(int i)
{
    m_i = i;
}

int NestedClassesOuter::NestedClassesInner::vmeth()
{
    return 142;
}

int NestedClassesOuter::NestedClassesInner::call_vmeth()
{
    return vmeth();
}

int NestedClassesOuter::NestedClassesInner::Get_i()
{
    return m_i;
}

void NestedClassesOuter::NestedClassesInner::Set_i(int i)
{
    m_i = i;
}

void NestedClassesOuter::NestedClassesInner::overloaded()
{
    m_i = -10;
}

void NestedClassesOuter::NestedClassesInner::overloaded(double f)
{
    m_i *= f;
}

NestedClassesOuter::NestedClassesInner NestedClassReturnDependant::get()
{
    return NestedClassesOuter::NestedClassesInner();
}

int NestedClassArgDependant::get(const NestedClassesOuter::NestedClassesInner &i)
{
    return i.m_i;
}

OperatorsClass& OperatorsClass::operator+=(const OperatorsClass &rhs)
{
    x += rhs.x;
    y += rhs.y;
    return *this;
}

OperatorsClass& OperatorsClass::operator-=(const OperatorsClass &rhs)
{
    x -= rhs.x;
    y -= rhs.y;
    return *this;
}

int ArrayClass::sum(ArrayClass *objs, int len)
{
    int total = 0;
    for(int i = 0; i < len; i++)
        total += objs[i].m_i;

    return total;
}
