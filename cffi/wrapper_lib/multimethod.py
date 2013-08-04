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

    def overload(self, *args, **kwargs):
        """
        Add a new overload to the multimethod.

        Args
        """
        def closure(func):
            self.overloads.append(Overload(func, args, kwargs))
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
        args, kwargs = overload.convert_args(args, kwargs)
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
        args, kwargs = overload.convert_args(args, kwargs)

        return overload.func(instance, *args, **kwargs)

class Overload(object):
    def __init__(self, func, args, kwargs):
        self.func = func
        self.args = []
        self.kwargs = kwargs
        self.required_count = 0

        for (i, a) in enumerate(args):
            if isinstance(a, str):
                if a not in kwargs:
                    raise TypeError("named positional argument '%s' at "
                                    "position %d does match any keyword "
                                    "arguments" % (a, i))
                self.args.append((kwargs[a], a))
            else:
                if i > 0 and self.args[-1][1] is not None:
                    raise TypeError("unnamed positional argument at position "
                                    "%d follows a named positional argument."
                                    % i)
                self.args.append((a, None))
                self.required_count += 1
        

    def check_match(self, args, kwargs):
        """
        Checks if the given arguments match this overload. Returns an error
        message if the arguments don't match.
        """
        if len(args) < self.required_count:
            return "not enough arguments"
        elif len(args) > len(self.args):
            return "too many arguments"

        for i, arg_value in enumerate(args):
            arg_type, arg_name = self.args[i]
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
        return True

    def convert_args(self, args, kwargs):
        """
        Convert the arguments passed to the types specified in the signature
        if necessary.
        """
        new_args = list(args)
        new_kwargs = dict(kwargs)
        for i, arg_value in enumerate(args):
            arg_type, arg_name = self.args[i]
            # Use issubclass here so we won't invoke __instancecheck__ twice
            if (not issubclass(type(arg_value), arg_type) and
                hasattr(arg_type, 'convert')):
                # only try to convert arg_value if it isn't already the correct
                # type
                new_args[i] = arg_type.convert(arg_value)

        for arg_name, arg_value in kwargs.iteritems():
            arg_type = self.kwargs[arg_name]
            if (not issubclass(type(arg_value), arg_type) and
                hasattr(arg_type, 'convert')):
                new_kwargs[arg_name] = arg_type.convert(arg_value)

        return (tuple(new_args), new_kwargs)
