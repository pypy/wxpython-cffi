import functools

from cppwrapper import CppWrapper

@classmethod
def abstract__new__(cls, *args, **kwargs):
    raise TypeError('%s cannot be instantiated or sub-classed' % cls.__name__)

@classmethod
def purevirtual__new__(cls, *args, **kwargs):
    raise TypeError("%s represents a C++ abstract class and cannot be "
                    "instantiated" % cls.__name__)

def abstract_class(cls):
    '''
    @staticmethod
    def __new__(cls, *args, **kwargs):
        if '_override_abstract_class' in kwargs:
            return super(base_class, cls).__new__(cls, *args, **kwargs)
    base_class.__new__ = __new__
    return base_class
    '''
    cls.__new__ = abstract__new__
    return cls

def concrete_subclass(cls):
    '''
    @staticmethod
    def __new__(cls, *args, **kwargs):
        kwargs['_override_abstract_class'] = True
        return super(base_class, cls).__new__(cls, *args, **kwargs)
    base_class.__new__ = __new__
    return base_class
    '''
    cls.__new__ = staticmethod(CppWrapper.__new__)
    return cls

def purevirtual_abstract_class(cls):
    '''
    @staticmethod
    def __new__(cls, *args, **kwargs):
        if cls is base_class:
        return super(base_class, cls).__new__(cls, *args, **kwargs)
    base_class.__new__ = __new__
    return base_class
    '''
    cls.__new__ = purevirtual__new__
    return cls
