from .defaults import DefaultArgIndicator

class MMTypeCheckMeta(type):
    def __instancecheck__(self, instance):
        return self.__instancecheck__(instance)

    def __subclasscheck__(self, cls):
        return issubclass(cls, self.getclass())

class MMTypeError(Exception):
    def __init__(self, name, type):
        self.name = name
        self.type = type

    @property
    def message(self):
        return ("argument '%s' has unexpected type '%s'" %
                (self.name, self.type))

class MMInternalError(Exception):
    def __init__(self, e):
        self.exception = e

def check_args_types(*args):
    for a in args:
        arg_name, arg_type, arg_value = a

        if not isinstance(arg_value, (arg_type, DefaultArgIndicator)):
            raise TypeError("argument '%s' has unexpected type '%s'" %
                            (arg_name, type(arg_value)))

def check_arg_type(arg_name, arg_type, arg_value):
    if not isinstance(arg_value, (arg_type, DefaultArgIndicator)):
        raise MMTypeError(arg_name, type(arg_value))

def raise_mm_arg_failure(exception_list):
    errmsgs = []

    for i, e in enumerate(exception_list):
        prefix = "overload #%d: " % i
        # The two types of exceptions that should be seen are:
        # TypeError, which come from the *args, **kwargs conversion failing
        # MMTypeError, which come from a parameter having the wrong type
        errmsgs.append(prefix + e.message)

    raise TypeError('arguments did not match any overloaded call:\n%s' %
                    '\n'.join(errmsgs))
