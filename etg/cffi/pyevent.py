import etgtools
import etgtools.tweaker_tools as tools

from etgtools.extractors import ClassDef, CppMethodDef_cffi, ParamDef

def setupPyEvent(cls):
    cls.addItem(CppMethodDef_cffi(
        cls.name, isCtor=True,
        pyArgs=etgtools.ArgsString('(WL_Self self, int id=0, int eventType=wrapper_lib.default_arg_indicator)'),
        pyBody="""\
        if eventType is wrapper_lib.default_arg_indicator:
            eventType = wxEVT_NULL
        d = dict()
        with wrapper_lib.get_refcounted_handle(d) as handle:
            ptr = call(int(id), int(eventType), handle)

        wrapper_lib.init_wrapper(self, ptr, wrapper_lib.hassubclass(self))
        self._dict = d
        """,
        cReturnType='void*',
        cArgsString='(int id, int eventType, void *handle)',
        cBody="return new WL_CLASS_NAME(id, eventType, handle);",
        originalCppArgs=etgtools.ArgsString('(int id, int eventType, void *handle)'),
    ))

    cls.addItem(CppMethodDef_cffi(
        '__getattr__', 
        pyArgs=etgtools.ArgsString('(WL_Self self, WL_Self attr)'),
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
        '__delattr__',
        pyArgs=etgtools.ArgsString('(WL_Self self, WL_Self attr)'),
        pyBody="""\
        if not attr in _dict:
            raise AttributeError(attr)
        del self._dict[attr]
        """))

    cls.addItem(CppMethodDef_cffi(
        '__setattr__',
        pyArgs=etgtools.ArgsString('(WL_Self self, WL_Object attr, WL_Object value)'),
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
        '_getAttrDict',
        pyArgs=etgtools.ArgsString('(WL_Self self)'),
        pyBody="""\
        return ffi.from_handle(call(wrapper_lib.get_ptr(self)))
        """,
        cReturnType='void*',
        cArgsString='(void *self)',
        cBody="""\
        return ((%s*)self)->m_dict_ref.get_handle();
        """ % cls.name,
    ))

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
