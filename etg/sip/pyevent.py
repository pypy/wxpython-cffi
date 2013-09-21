from etgtools.extractors import ClassDef, MethodDef, ParamDef

def run(module):
    cls = ClassDef(name='wxPyEvent', bases=['wxEvent'], 
        briefDoc="""\
            :class:`PyEvent` can be used as a base class for implementing custom
            event types in Python. You should derive from this class instead
            of :class:`Event` because this class is Python-aware and is able to
            transport its Python bits safely through the wxWidgets event
            system and have them still be there when the event handler is
            invoked. Note that since :class:`PyEvent` is taking care of preserving
            the extra attributes that have been set then you do not need to
            override the Clone method in your derived classes.
            
            :see: :class:`PyCommandEvent`""",
        items=[
            MethodDef(name='wxPyEvent', isCtor=True, items=[
                ParamDef(type='int', name='id', default='0'),
                ParamDef(type='wxEventType', name='eventType', default='wxEVT_NULL'),
                ]),

            MethodDef(name='__getattr__', type='PyObject*', items=[
                ParamDef(type='PyObject*', name='name'),],
                cppCode=("sipRes = sipCpp->__getattr__(name);", "sip")),
            
            MethodDef(name='__delattr__', type='void', items=[
                ParamDef(type='PyObject*', name='name'),],
                cppCode=("sipCpp->__delattr__(name);", "sip")),
            
            MethodDef(name='__setattr__', type='void', items=[
                ParamDef(type='PyObject*', name='name'),
                ParamDef(type='PyObject*', name='value'),], 
                cppCode=("sipCpp->__setattr__(name, value);", "sip")),
            
            MethodDef(name='Clone', type='wxEvent*', isVirtual=True, isConst=True, factory=True),
            MethodDef(name='_getAttrDict', type='PyObject*'),
            ])
    
    module.addItem(cls)
    cls.addHeaderCode('#include "pyevent.h"')

    cls = ClassDef(name='wxPyCommandEvent', bases=['wxCommandEvent'], 
        briefDoc="""\
            :class:`PyCommandEvent` can be used as a base class for implementing
            custom event types in Python. You should derive from this class
            instead of :class:`CommandEvent` because this class is Python-aware
            and is able to transport its Python bits safely through the
            wxWidgets event system and have them still be there when the
            event handler is invoked. Note that since :class:`PyCommandEvent` is
            taking care of preserving the extra attributes that have been set
            then you do not need to override the Clone method in your
            derived classes.
            
            :see: :class:`PyEvent`""",
        items=[
            MethodDef(name='wxPyCommandEvent', isCtor=True, items=[
                ParamDef(type='wxEventType', name='eventType', default='wxEVT_NULL'),
                ParamDef(type='int', name='id', default='0'),
                ]),
            
            MethodDef(name='__getattr__', type='PyObject*', items=[
                ParamDef(type='PyObject*', name='name'),],
                cppCode=("sipRes = sipCpp->__getattr__(name);", "sip")),
            
            MethodDef(name='__delattr__', type='void', items=[
                ParamDef(type='PyObject*', name='name'),],
                cppCode=("sipCpp->__delattr__(name);", "sip")),
            
            MethodDef(name='__setattr__', type='void', items=[
                ParamDef(type='PyObject*', name='name'),
                ParamDef(type='PyObject*', name='value'),], 
                cppCode=("sipCpp->__setattr__(name, value);", "sip")),
            
            MethodDef(name='Clone', type='wxEvent*', isVirtual=True, isConst=True, factory=True),
            MethodDef(name='_getAttrDict', type='PyObject*'),
            ])
    
    module.addItem(cls)
    cls.addHeaderCode('#include "pyevent.h"')
