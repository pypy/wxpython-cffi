import re

check_operator = re.compile(r'^\s*operator(?P<opname>[^A-Za-z0-9_]+)\s*$')
const_ref = re.compile(r'^\s*const\s+(?P<name>[A-Za-z0-9_]+)\s*&\s*$')

def get_operator(meth):
    match = check_operator.match(meth.name)
    if match is None:
        return None

    opname = match.groups()[0].strip()

    if len(meth.params) == 1:
        cls = UnaryCppOperator
    elif len(meth.params) == 2:
        cls = BinaryCppOperator
    else:
        cls = NaryCppOperator

    if opname in cls.OPERATORS:
        return cls(opname)

    raise Exception("Unknown operator %s" % meth.name)
    return None

def get_standalone_operator(func):
    # Operators defined outside of the class.
    match = check_operator.match(func.name)
    if match is None:
        return None

    opname = match.groups()[0].strip()

    if len(func.params) < 1:
        return None
    match = const_ref.match(func.params[0].item.type)
    if match is None:
        return None
    class_name = match.group(1)

    if len(func.params) == 1:
        cls = UnaryCppOperator
    elif len(func.params) == 2:
        cls = BinaryCppOperator
    else:
        raise NotImplementedError

    if opname in cls.OPERATORS:
        return class_name, cls(opname)

    return None

class CppOperator(object):
    def __new__(cls, name):
        if name in cls._cache:
            return cls._cache[name]

        obj = super(CppOperator, cls).__new__(cls, name)
        cls._cache[name] = obj
        return obj

    def __init__(self, name):
        self.name = name
        self.pyname = self.OPERATORS[name][0]

class UnaryCppOperator(CppOperator):
    OPERATORS = {
        '-'     : ('__neg__', '-%s')
    }
        # This one is hard because we may have to change return types?
        #'operator bool' : '__int__',  # Why not __nonzero__?

    _cache = { }

    def cpp_code(self, arg):
        return self.OPERATORS[self.name][1] % arg

class BinaryCppOperator(CppOperator):
    OPERATORS = {
        '!='    : ('__ne__',   '%s != %s'),
        '=='    : ('__eq__',   '%s == %s'),
        '<'     : ('__lt__',   '%s < %s'),
        '<='    : ('__le__',   '%s <= %s'),
        '>'     : ('__gt__',   '%s > %s'),
        '>='    : ('__ge__',   '%s >= %s'),
        '+'     : ('__add__',  '%s + %s'),
        '-'     : ('__sub__',  '%s - %s'),
        '*'     : ('__mul__',  '%s * %s'),
        '/'     : ('__div__',  '%s / %s'),
        '+='    : ('__iadd__', '%s += %s'),
        '-='    : ('__isub__', '%s -= %s'),
        '*='    : ('__imul__', '%s *= %s'),
        '/='    : ('__idiv__', '%s /= %s'),
    }

    _cache = { }

    def cpp_code(self, lfs, rhs):
        return self.OPERATORS[self.name][1] % (lfs, rhs)

class NaryCppOperator(CppOperator):
    # There is only one N-ary operator in C++...
    OPERATORS = {
        '()'   : ('__call__', '%s(%s)'),
    }

    _cache = { }

    def cpp_code(self, obj, *args):
        return self.OPERATORS[self.name][1] % (obj, ', '.join(args))
