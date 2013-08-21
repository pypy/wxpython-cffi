#include <string>
#include <cstdlib>
#include <cstring>

using std::string;

extern "C" string* cffimtype_string_c2cpp(char *c_obj)
{
    return new string(c_obj);
}

char* cffimtype_string_cpp2c(string *cpp_obj)
{
    char *charp = (char*)malloc(sizeof(char) * cpp_obj->size() + 1);
    strcpy(charp, cpp_obj->c_str());
    return charp;
}

string global_string = string("global");
extern "C" char *cffigvar_global_string = cffimtype_string_cpp2c(&global_string);

int string_len(string *str)
{
    return str->size();
}

int total_string_len(string *strs, int len)
{
    int total = 0;
    for(int i = 0; i < len; i++)
        total += strs[i].size();
    return total;
}

extern "C" string * (*get_string_fake_virtual_ptr)();
string string_len_fake_virtual()
{
    string *virtual_res = get_string_fake_virtual_ptr();
    string tmp(*virtual_res);
    delete virtual_res;
    return tmp;
}

int string_len_cb()
{
    return string_len_fake_virtual().size();
}


extern "C" int cffifunc_string_len_cb()
{
    return string_len_cb();
}

extern "C" int cffifunc_string_len(char *s)
{
    string *v0_tmp = cffimtype_string_c2cpp(s);

    int return_tmp =  string_len(v0_tmp);

    delete v0_tmp;
    return return_tmp;
}

extern "C" int cffifunc_total_string_len(char **s, int len)
{
    string *v0_tmp = new string[len];
    for(int i = 0; i < len; i++)
    {
        string *c2cpp_tmp = cffimtype_string_c2cpp(s[i]);
        v0_tmp[i] = *c2cpp_tmp;
        delete c2cpp_tmp;
    }

    int return_tmp = total_string_len(v0_tmp, len);

    delete[] v0_tmp;
    return return_tmp;
}
