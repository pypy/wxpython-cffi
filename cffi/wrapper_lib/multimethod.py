import inspect

class MMTypeCheckMeta(type):
    def __instancecheck__(self, instance):
        return self.__instancecheck__(instance)

    def __subclasscheck__(self, cls):
        return issubclass(cls, self.getclass())

class Multimethod(object):
    def __init__(self, outofbody_overloads=False):
        self.overloads = []
        if outofbody_overloads:
            self.get = self.get_self
        else:
            self.get = self.get_partial

    def overload(self, **kwargs):
        """
        Add a new overload to the multimethod.
        """
        def closure(func):
            self.overloads.append(Overload(func, True, kwargs))
            return self
        return closure

    def finish(self):
        """
        Stop accepting overloads from outside the class body and instead return
        a partial when accessed.
        """
        self.get = self.get_partial

    def resolve_overload(self, args, kwargs):
        errmsgs = []
        for overload in self.overloads:
            match = overload.check_match(args, kwargs)
            if match is True:
                return overload
            errmsgs.append(match)
        else:
            raise TypeError('arguments did not match any overloaded call: %s' %
                            errmsgs)

    def __call__(self, *args, **kwargs):
        overload = self.resolve_overload(args, kwargs)
        return overload.func(*args, **kwargs)

    def get_self(self, instance, owner):
        return self

    def get_partial(self, instance, owner):
        return MultimethodPartial(self.resolve_overload, instance)

    def __get__(self, instance, owner):
        return self.get(instance, owner)

class StaticMultimethod(Multimethod):
    def get_partial(self, instance, owner):
        return self

    def overload(self, **kwargs):
        """
        Add a new overload to the multimethod.
        """
        def closure(func):
            self.overloads.append(Overload(func, False, kwargs))
            return self
        return closure

class ClassMultimethod(Multimethod):
    def get_partial(self, instance, owner):
        return MultimethodPartial(self.resolve_overload, owner)

class MultimethodPartial(object):
    def __init__(self, resolve, instance):
        self.resolve = resolve
        self.instance = instance

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            instance = args[0]
            args = args[1:]
        else:
            instance = self.instance
        overload = self.resolve(args, kwargs)

        return overload.func(instance, *args, **kwargs)

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
