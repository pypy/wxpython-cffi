import warnings
import functools

def deprecated(arg):
    if isinstance(arg, str):
        return deprecated_method(arg)
    else:
        return deprecated_func(arg)


def deprecated_func(func, message="{0}() is deprecated"):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn_explicit(message.format(func.__name__),
                                category=DeprecationWarning,
                                filename=func.func_code.co_filename,
                                lineno=func.func_code.co_firstlineno + 1)

        return func(*args, **kwargs)
    wrapper._wrapped_func = func
    return wrapper

def deprecated_method(cls_name):
    def closure(func):
        if func.__name__ == '__init__':
            message = cls_name + " constructor is deprecated"
        else:
            message = cls_name + ".{0}() is deprecated"
        return deprecated_func(func, message)
    return closure
