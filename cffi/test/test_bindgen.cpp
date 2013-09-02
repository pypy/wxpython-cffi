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

int std_string_len(string *str)
{
    return str->size();
}

int std_string_len(string *str, int len)
{
    int total = 0;
    for(int i = 0; i < len; i++)
        total += str[i].size();
    return total;
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

int ArrayClass::sum_virt(ArrayClass *objs, int len)
{
    int total = 0;
    for(int i = 0; i < len; i++)
        total += objs[i].m_i;

    return total;
}

int ArrayClass::call_sum_virt(ArrayClass *objs, int len)
{
    return sum_virt(objs, len);
}

IntWrapper IntWrapperClass::trivial_mappedtype(IntWrapper i, IntWrapper &k)
{
    k.i = 100;
    return IntWrapper(i.i - 1);
}

IntWrapper IntWrapperClass::call_trivial_mappedtype(IntWrapper i, IntWrapper &k)
{
    return trivial_mappedtype(i, k);
}

IntWrapper IntWrapperClass::trivial_inout_mappedtype(IntWrapper i, IntWrapper &k)
{
    k.i *= 100;
    return IntWrapper(i.i - 1);
}

IntWrapper IntWrapperClass::call_trivial_inout_mappedtype(IntWrapper i, IntWrapper &k)
{
    return trivial_mappedtype(i, k);
}

string MappedTypeClass::get_name()
{
    return m_name;
}

string MappedTypeClass::call_get_name()
{
    return get_name();
}

string MappedTypeClass::concat(string *s, int len)
{
    string out;
    for(int i = 0; i < len; i++)
        out += s[i];
    return out;
}

string MappedTypeClass::call_concat(string *s, int len)
{
    return concat(s, len);
}

int OutClass::get_coords_ptr(int *x, int *y)
{
    *x = 3;
    *y = 6;

    return 9;
}

int OutClass::get_coords_ref(int &x, int &y)
{
    x = 3;
    y = 6;

    return 9;
}

void OutClass::get_wrappedtype_ptr(CtorsClass *x, CtorsClass **y)
{
    *x = CtorsClass(15);
    *y = new CtorsClass(30);
}

void OutClass::get_wrappedtype_ref(CtorsClass &x, CtorsClass *&y)
{
    x = CtorsClass(45);
    y = new CtorsClass(60);
}

void OutClass::get_mappedtype_ptr(string *x, string **y)
{
    *x = string("15");
    *y = new string("30");
}

void OutClass::get_mappedtype_ref(string &x, string *&y)
{
    x = string("45");
    y = new string("60");
}

int OutClass::call_get_coords_ptr(int *x, int *y)
{
    return get_coords_ptr(x, y);
}

int OutClass::call_get_coords_ref(int &x, int &y)
{
    return get_coords_ref(x, y);
}

void OutClass::call_get_mappedtype_ptr(string *x, string **y)
{
    get_mappedtype_ptr(x, y);
}

void OutClass::call_get_mappedtype_ref(string &x, string *&y)
{
    get_mappedtype_ref(x, y);
}

void OutClass::call_get_wrappedtype_ptr(CtorsClass *x, CtorsClass **y)
{
    get_wrappedtype_ptr(x, y);
}

void OutClass::call_get_wrappedtype_ref(CtorsClass &x, CtorsClass *&y)
{
    get_wrappedtype_ref(x, y);
}

void InOutClass::double_ptr(int *i)
{
    *i *= 2;
}

void InOutClass::double_ref(int &i)
{
    i *= 2;
}

void InOutClass::double_ptr(CtorsClass *i)
{
    *i = CtorsClass(i->get() * 2);
}

void InOutClass::double_ref(CtorsClass &i)
{
    i = CtorsClass(i.get() * 2);
}

void InOutClass::double_ptr(Vector *i)
{
    i->i *= 2;
    i->j *= 2;
}

void InOutClass::double_ref(Vector &i)
{
    i.i *= 2;
    i.j *= 2;
}

void InOutClass::call_double_ptr(int *i)
{
    double_ptr(i);
}

void InOutClass::call_double_ref(int &i)
{
    double_ref(i);
}

void InOutClass::call_double_ptr(CtorsClass *i)
{
    double_ptr(i);
}

void InOutClass::call_double_ref(CtorsClass &i)
{
    double_ref(i);
}

void InOutClass::call_double_ptr(Vector *i)
{
    double_ptr(i);
}

void InOutClass::call_double_ref(Vector &i)
{
    double_ref(i);
}

SmartVector double_vector(SmartVector &vec)
{
    return SmartVector(vec.x * 2, vec.y * 2);
}

long AllowNoneClass::get_addr_ptr(SmartVector *v)
{
    return (long)v;
}

long AllowNoneClass::get_addr_ref(SmartVector &v)
{
    return (long)&v;
}
