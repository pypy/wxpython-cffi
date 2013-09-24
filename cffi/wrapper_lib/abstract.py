import functools

from cppwrapper import CppWrapper

@classmethod
def abstract__new__(cls, *args, **kwargs):
    raise TypeError('%s cannot be instantiated or sub-classed' % cls.__name__)

def purevirtual__new__(cls, *args, **kwargs):
    if cls is kwargs['_baseclass']:
        raise TypeError("%s represents a C++ abstract class and cannot be "
                        "instantiated" % cls.__name__)
    else:
        del kwargs['_baseclass']
        return CppWrapper.__new__(cls, *args, **kwargs)

def abstract_class(cls):
    cls.__new__ = abstract__new__
    return cls

def concrete_subclass(cls):
    cls.__new__ = staticmethod(CppWrapper.__new__)
    return cls

def purevirtual_abstract_class(cls):
    cls.__new__ = functools.partial(
        purevirtual__new__, _baseclass=cls)
    return cls
