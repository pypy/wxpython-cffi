class Multimethod(object):
    def __init__(self):
        self.overloads = []

    def overload(self, *args, **kwargs):
        def closure(func):
            self.overloads.append(Overload(func, args, kwargs))
            return self
        return closure

    def resolve_overload(self, args, kwargs):
        errmsgs = []
        for overload in self.overloads:
            match = overload.check_match(args, kwargs)
            if match is True:
                return overload.func
            errmsgs.append(match)
        raise TypeError('arguments did not match any overloaded call: %s' %
                            errmsgs)

    def __call__(self, *args, **kwargs):
        return self.resolve_overload(args, kwargs)(*args, **kwargs)

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return MultimethodPartial(self.resolve_overload, instance)

class StaticMultimethod(Multimethod):
    def __get__(self, instance, owner):
        return self

class ClassMultimethod(Multimethod):
    def __get__(self, instance, owner):
        return MultimethodPartial(self.resolve_overload, owner)

class MultimethodPartial(object):
    def __init__(self, resolve, instance):
        self.resolve = resolve
        self.instance = instance

    def __call__(self, *args, **kwargs):
        return self.resolve(args, kwargs)(self.instance, *args, **kwargs)

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

        for arg_name in kwargs:
            if arg_name not in self.kwargs:
                return "'%s' is not a valid keyword argument" % arg_name
            if not isinstance(kwargs[arg_name], self.kwargs[arg_name]):
                return ("argument '%s' has unexpected type '%s'" %
                        (arg_name, self.kwargs[arg_name]))
        return True
