class NoDtorObj
{
public:
    ~NoDtorObj();
};

class DtorObjBase
{
public:
    virtual ~DtorObjBase() { };
    virtual int virtual_meth(int);
};

class DtorObj : public DtorObjBase
{
public:
    virtual ~DtorObj();
    int non_virtual_meth(int);
    virtual int virtual_meth(int);
};

#define METHIDX_DtorObj_88_virtual_meth 1

extern "C"
{
    int deleted_count = 0;

    int call_virtual_meth(void *obj, int i)
    {
        return ((DtorObj*)obj)->virtual_meth(i);
    }

    void (*DtorObj_vtable[2])();

    void* DtorObj_88__op_new()
    {
        return new DtorObj;
    }

    void DtorObj_88__op_delete(void *self)
    {
        delete (DtorObj*)self;
    }

    int DtorObj_88_non_virtual_meth(void *self, int i)
    {
        return ((DtorObj*)self)->non_virtual_meth(i);
    }

    int DtorObj_88_virtual_meth(void *self, int i)
    {
        return ((DtorObj*)self)->DtorObjBase::virtual_meth(i);
    }

    void* NoDtorObj_88__op_new()
    {
        return new NoDtorObj;
    }

    void NoDtorObj_88__op_delete(void *obj)
    {
        delete (NoDtorObj*)obj;
    }
}

NoDtorObj::~NoDtorObj()
{
    deleted_count++;
}

int DtorObjBase::virtual_meth(int i)
{
    return i;
}

DtorObj::~DtorObj()
{
    deleted_count++;
    ((void(*)(void*))DtorObj_vtable[0])(this);
}

int DtorObj::non_virtual_meth(int i)
{
    return i;
}

#include <cstdio>
extern "C" typedef int(*FPTR_DtorObj_88_virtual_meth)(void*, int);
int DtorObj::virtual_meth(int i)
{
    printf("%p\n", DtorObj_vtable[METHIDX_DtorObj_88_virtual_meth]);
    return ((FPTR_DtorObj_88_virtual_meth)DtorObj_vtable[METHIDX_DtorObj_88_virtual_meth])(this, i);
}
