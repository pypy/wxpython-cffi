#include <cstring>

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
    DtorObj();
    virtual ~DtorObj();
    int non_virtual_meth(int);
    virtual int virtual_meth(int);

    char vflags[2];
};

#define METHIDX_DtorObj_88_virtual_meth 1

extern "C"
{
    int deleted_count = 0;

    int call_virtual_meth(void *obj, int i)
    {
        return ((DtorObj*)obj)->virtual_meth(i);
    }

    void* create_DtorObj()
    {
        return new DtorObj;
    }

    void (*DtorObj_vtable[2])();

    void DtorObj_set_vflag(void* self, int i)
    {
        ((DtorObj*)self)->vflags[i] = 1;
    }

    void DtorObj_set_vflags(void* self, char* flags)
    {
        memcpy(((DtorObj*)self)->vflags, flags, sizeof(((DtorObj*)self)->vflags));
    }

    void* DtorObj_88_DtorObj()
    {
        return new DtorObj;
    }

    void DtorObj_88_delete(void *self)
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

    void* NoDtorObj_88_NoDtorObj()
    {
        return new NoDtorObj;
    }

    void NoDtorObj_88_delete(void *obj)
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

DtorObj::DtorObj()
{
    memset(this->vflags, 0, sizeof(this->vflags));
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

extern "C" typedef int(*FPTR_DtorObj_88_virtual_meth)(void*, int);
int DtorObj::virtual_meth(int i)
{
    if(this->vflags[1])
        return ((FPTR_DtorObj_88_virtual_meth)DtorObj_vtable[METHIDX_DtorObj_88_virtual_meth])(this, i);
    else
        return this->DtorObjBase::virtual_meth(i);
}
