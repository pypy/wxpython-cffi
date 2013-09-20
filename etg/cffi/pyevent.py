import etgtools.tweaker_tools as tools

from etgtools.extractors import ClassDef, CppMethodDef_cffi, ParamDef

def setupPyEvent(cls):
    cls.addItem(CppMethodDef_cffi(
        'void*', cls.name,
        '(int id, int eventType, void *handle)',
        #'(self, id=0, eventType=wrapper_lib.LD("wxEVT_NULL"))', isCtor=True,
        '(self, id=0, eventType=wrapper_lib.LD("wxEVT_NULL"))', isCtor=True,
        pyArgs=[ParamDef(name='id', type='numbers.Number'),
                ParamDef(name='eventType', type='numbers.Number')],
        callArgs='(id, eventType, handle)',
        body="return new cfficlass_%s(id, eventType, handle);" % cls.name,
        pyBody="""\
        wrapper_lib.check_args_types(numbers.Number, id, "id",
                                     numbers.Number, eventType, "eventType")

        d = dict()
        with wrapper_lib.get_refcounted_handle(d) as handle:
            ptr = call(int(id), int(eventType), handle)

        wrapper_lib.CppWrapper.__init__(self, ptr)
        self._dict = d
        """))

    cls.addItem(CppMethodDef_cffi(
        'void', '__getattr__', '()', '(self, attr)', body="",
        pyBody="""\
        if attr == '_dict':
            # The only way __getattr__ can be called for '_dict' is if an
            # attribute that doesn't exist is being looked up before _dict is
            # set.
            raise KeyError
        try:
            return self._dict[attr]
        except KeyError:
            raise AttributeError(attr)
        """))

    cls.addItem(CppMethodDef_cffi(
        'void', '__delattr__', '()', '(self, attr)', body="",
        pyBody="""\
        if not attr in _dict:
            raise AttributeError(attr)
        del self._dict[attr]
        """))

    cls.addItem(CppMethodDef_cffi(
        'void', '__setattr__', '()', '(self, attr, value)', body="",
        pyBody="""\
        # Until the custom dict is set, store attributes directly on the object
        # Additionally, if the attribute is already stored on the object, store
        # the new value on the object too.
        if not hasattr(self, '_dict') or (hasattr(self, attr) and
                                          attr not in self._dict) :
            super(%s, self).__setattr__(attr, value)
        else:
            self._dict[attr] = value
        """ % tools.removeWxPrefix(cls.name)))
            
    cls.addMethod(
        'wxEvent*', 'Clone', '()', isVirtual=True, isConst=True, factory=True)

    cls.addItem(CppMethodDef_cffi(
        'void*', '_getAttrDict', '(void *self)', '(self)',
        body="""\
        return ((%s*)self)->m_dict_ref.get_handle();
        """ % cls.name,
        pyBody="""\
        return ffi.from_handle(call(wrapper_lib.get_ptr(self)))
        """))

    # Retrieve the attribute dictionary so that attributes will persist even
    # after an event has been copied by C++
    cls.pyCode_cffi = """\
    @classmethod
    def _from_ptr(cls, ptr, py_owned=False, external_ref=False):
        obj = cls.__new__(cls, _override_abstract_class=True)
        CppWrapper.__init__(obj, ptr, py_owned, False, external_ref)
        obj._dict = obj._getAttrDict()

        return obj
    """

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
            
            :see: :class:`PyCommandEvent`""")
    setupPyEvent(cls)
    module.addItem(cls)
    cls.addHeaderCode('#include "cffi/pyevent.h"')

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
            
            :see: :class:`PyEvent`""")
    setupPyEvent(cls)
    module.addItem(cls)
    cls.addHeaderCode('#include "cffi/pyevent.h"')
