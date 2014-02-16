import inspect
import functools

from .lazy_defaults import eval_func_defaults
from .defaults import DefaultArgIndicator

class MMTypeCheckMeta(type):
    def __instancecheck__(self, instance):
        return self.__instancecheck__(instance)

    def __subclasscheck__(self, cls):
        return issubclass(cls, self.getclass())

class Multimethod(object):
    _skip_first = True
    def __init__(self, func=None):
        self._overloads = []
        self._get = self._get_partial
        if func is not None:
            functools.update_wrapper(self, func)

    def overload(self, **kwargs):
        """
        Add a new overload to the multimethod.
        """
        if any(isinstance(a, str) for a in kwargs.itervalues()):
            self._get = self._get_self
        def closure(func):
            self._overloads.append(Overload(func, self._skip_first, kwargs))
            return self
        return closure

    def deprecated_overload(self, *args, **kwargs):
        """
        Add an overload to the multimethod that will print a deprecated warning
        when called.
        """
        if any(isinstance(a, str) for a in kwargs.itervalues()):
            self._get = self._get_self
        def closure(func):
            try:
                self._overloads.append(DeprecatedOverload(
                    func, self._skip_first, kwargs, args[0]))
            except IndexError:
                self._overloads.append(DeprecatedOverload(
                    func, self._skip_first, kwargs, None))
            return self
        return closure

    def finalize(self):
        """
        Stop accepting overloads from outside the class body and instead return
        a partial when accessed.
        """
        self._get = self._get_partial
        for overload in self._overloads:
            overload.finalize()

    def _resolve_overload(self, args, kwargs):
        errmsgs = []
        for overload in self._overloads:
            match = overload.check_match(args, kwargs)
            if match is True:
                return overload
            errmsgs.append(match)
        else:
            raise TypeError('arguments did not match any overloaded call: %s' %
                            errmsgs)

    def __call__(self, *args, **kwargs):
        overload = self._resolve_overload(args, kwargs)
        return overload.func(*args, **kwargs)

    def _get_self(self, instance, owner):
        return self

    def _get_partial(self, instance, owner):
        return MultimethodPartial(self, instance)

    def __get__(self, instance, owner):
        return self._get(instance, owner)

class StaticMultimethod(Multimethod):
    _skip_first = False
    def _get_partial(self, instance, owner):
        return self

class ClassMultimethod(Multimethod):
    def _get_partial(self, instance, owner):
        return MultimethodPartial(self, owner)

class MultimethodPartial(object):
    def __init__(self, mm, instance):
        self.resolve = mm._resolve_overload
        self.instance = instance

        self.__name__ = getattr(mm, '__name__', '')
        self.__doc__ = getattr(mm, '__doc__', '')

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            instance = args[0]
            args = args[1:]
        else:
            instance = self.instance
        overload = self.resolve(args, kwargs)

        return overload.func(instance, *args, **kwargs)

    __func__ = property(lambda self: self.resolve.__self__)

class Overload(object):
    def __init__(self, func, ignore_first, kwargs):
        argspec = inspect.getargspec(func)
        args = argspec.args
        if ignore_first:
            args = args[1:]

        for i, a in enumerate(args):
            if a not in kwargs:
                raise TypeError("named positional argument '%s' at position %d"
                                " does match any keyword arguments" % (a, i))
        for a in kwargs:
            if a not in argspec.args:
                raise TypeError("keyword argument '%s' does not match any "
                                "positional arguments" % a)

        self.func = func
        self.args = [(a, kwargs[a]) for a in args]
        self.kwargs = kwargs

        if argspec.defaults is None:
            self.required_args = set(args)
        else:
            self.required_args = set(args[:-len(argspec.defaults)])


    def check_match(self, args, kwargs):
        """
        Checks if the given arguments match this overload. Returns an error
        message if the arguments don't match.
        """
        total_args = len(args) + len(kwargs)
        if total_args > len(self.args):
            return "too many arguments"
        elif total_args < len(self.required_args):
            return "too many arguments"

        provided_required_args = len(args)

        for i, arg_value in enumerate(args):
            arg_name, arg_type = self.args[i]
            if arg_name in kwargs:
                return ("argument '%s' has already been given as a positional "
                        "argument" % arg_name)
            if not isinstance(arg_value, arg_type):
                return "argument %d has unexptected type '%s'" % (i, arg_type)

        for arg_name, arg_value in kwargs.iteritems():
            if arg_name not in self.kwargs:
                return "'%s' is not a valid keyword argument" % arg_name

            arg_type = self.kwargs[arg_name]
            if not isinstance(arg_value, arg_type):
                return ("argument '%s' has unexpected type '%s'" %
                        (arg_name, arg_type))

            provided_required_args += int(arg_name in self.required_args)

        if provided_required_args < len(self.required_args):
            return "some required arguments are missing"

        return True

    def finalize(self):
        scope = self.func.func_globals
        for arg_name, arg_type in self.kwargs.iteritems():
            if isinstance(arg_type, str):
                self.kwargs[arg_name] = eval(arg_type, scope)
        self.args = [(name, self.kwargs[name]) for name, type in self.args]

        eval_func_defaults(self.func)

class DeprecatedOverload(Overload):
    def __init__(self, func, ignore_first, kwargs, cls_name=None):
        super(DeprecatedOverload, self).__init__(func, ignore_first, kwargs)
        if cls_name is None:
            self.func = deprecated(func)
        else:
            self.func = deprecated(cls_name)(func)

    def finalize(self):
        wrapper = self.func
        self.func = wrapper._wrapped_func
        super(DeprecatedOverload, self).finalize()
        self.func = wrapper


def check_args_types(*args):
    for a in args:
        arg_name, arg_type, arg_value = a

        if not isinstance(arg_value, (arg_type, DefaultArgIndicator)):
            raise TypeError("argument '%s' has unexpected type '%s'" %
                            (arg_name, type(arg_value)))

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
