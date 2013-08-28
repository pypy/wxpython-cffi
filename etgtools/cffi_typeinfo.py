import etgtools.extractors as extractors

# C basic types -> Python conversion functions
BASIC_CTYPES = {
    'int': 'int',
    'short': 'int',
    'long': 'int',
    'long long': 'int',
    'unsigned': 'int',
    'float': 'float',
    'double': 'float',
    'char': 'str',
    'char*': 'str',
    'char *': 'str',
    'signed char': 'int',
    'unsigned char': 'int',
    'bool': 'bool',
    'void': None,
}

ARRAY_SIZE_PARAM = 'array_size_'
OUT_PARAM_SUFFIX = '_ptr'

class TypeInfo(object):
    _cache = {}
    def __init__(self, typeName, typedef, **kwargs):
        if typeName == '' or typeName is None:
            typeName = 'void'
        self.name = typeName
        self.typedef = typedef
        self.ptrCount = typeName.count('*')
        self.isConst = 'const ' in typeName
        self.__dict__.update(kwargs)

        if self.out and self.inOut or (self.out or self.inOut) and self.array:
            raise TypeError('invalid combination of anotations.')


    @classmethod
    def new(cls, typeName, findItem, **kwargs):
        typeName = typeName.strip()
        isRef = False
        isPtr = False
        typedef = None

        name = typeName
        while True:
            isRef = (isRef or '&' in name)
            isPtr = (isPtr or '*' in name)
            name = (name.replace('::', '.').replace('const ', '').strip(' *&'))
            typedef = findItem(name) if name != '' else None
            if isinstance(typedef, extractors.TypedefDef):
                name = typedef.type
            else:
                break

        type = BasicTypeInfo
        if isinstance(typedef, extractors.ClassDef):
            type = WrappedTypeInfo
        elif isinstance(typedef, extractors.MappedTypeDef_cffi):
            type = MappedTypeInfo
        elif isPtr and 'char' in name:
            type = CharPtrTypeInfo

        key = (typeName, frozenset(kwargs.items()))
        if key not in cls._cache:
            typeInfo = type(typeName, isRef=isRef, isPtr=isPtr,
                            typedef=typedef, **kwargs)
            cls._cache[typeName] = typeInfo
            return typeInfo
        return cls._cache[key]

    @classmethod
    def clearCache(cls):
        cls._cache = {}

    def py2cPrecall(self, varName, inplace=False):
        return None

    def py2cParam(self, varName):
        return varName

    def py2cPostcall(self, varName):
        # Formerly called py2cReturn
        return None

    def c2py(self, varName):
        return varName

    def c2cppPrecall(self, varName):
        return None

    def c2cppParam(self, varName):
        return varName

    def c2cppPostcall(self, varName):
        return None

    def cpp2c(self, varName):
        return varName



class WrappedTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(WrappedTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.cType = self.typedef.unscopedName + ' *'
        self.cdefType = 'void *'
        self.cReturnType = self.typedef.name + ' *'
        self.overloadType = self.typedef.unscopedPyName

        if not self.inOut and (self.ptrCount == 2 or self.isRef and
                               self.isPtr):
            self.out = True

        if self.out or self.inOut:
            self.cType += '*'
            self.cdefType += '*'

        if self.array:
            self.cType += ' *'
            self.cdefType += '[]'

            cTypeArg = ', ctype="%s"' % self.cdefType
            self.overloadType = ("wrapper_lib.create_array_type(%s%s)" %
                                (self.typedef.unscopedPyName, cTypeArg))

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        if self.inOut:
            return """\
            {0} = wrapper_lib.get_ptr({0})
            {0}{1} = ffi.new('{2}', {0})
            """.format(varName, OUT_PARAM_SUFFIX, self.cdefType)
        if self.array:
            return ("{0}, {1}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2}).py2c({0})"
                    .format(varName, ARRAY_SIZE_PARAM, self.typedef.pyName,
                            self.cdefType))
        return None

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        if self.array:
            return varName
        return 'wrapper_lib.get_ptr(%s)' % varName

    def c2py(self, varName):
        if self.out or self.inOut:
            # TODO: if this is * or &, make it py-owned, and if it is ** or
            #       *&, make it cpp-owned
            return 'wrapper_lib.obj_from_ptr(%s[0], %s)' % (
                    varName, self.typedef.unscopedPyName)
        if self.array:
            return ("wrapper_lib.create_array_type({2}).c2py({0}, {1})"
                    .format(varName, ARRAY_SIZE_PARAM, self.typedef.pyName))
        return 'wrapper_lib.obj_from_ptr(%s, %s)' % (
                varName, self.typedef.unscopedPyName)

    def cpp2c(self, varName):
        if self.array:
            return "%s(%s, %s)" % (self.typedef.arraycpp2c, varName,
                                   ARRAY_SIZE_PARAM)
        # Always pass wrapped classes as pointers. If this is by value or
        # a const reference, it needs to be copy constructored onto the
        # heap, with Python taking ownership of the new object.
        if self.isPtr:
            return varName
        elif self.isRef and not self.isConst:
            return '&' + varName
        else:
            return "new %s(%s)" % (self.typedef.cppClassName, varName)

    def c2cppPrecall(self, varName):
        if self.out and self.ptrCount != 2 and not (self.ptrCount == 1 and
           self.isRef):
            # Only create a new object if the function expects a pointer, not a
            # reference to a pointer or a pointer to a a pointer
            return "*{0} = new {1};".format(varName, self.typedef.name)
        if self.array:
            return "{0} {1}_converted = {2}({1}, {3});".format(
                self.cReturnType, varName, self.typedef.arrayc2cpp,
                ARRAY_SIZE_PARAM)
        return None

    def c2cppParam(self, varName):
        if self.array:
            return varName + "_converted"
        if self.out or self.inOut:
            if self.isRef:
                return '*' * (2 - self.ptrCount) + varName
            elif self.ptrCount == 1:
                return '*' + varName
            else:
                return varName
        return ('*' if not self.isPtr else '') + varName

    def c2cppPostcall(self, varName):
        if self.array:
            return 'delete[] %s_converted;' % varName
        return None

class MappedTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(MappedTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.cType = self.typedef.cType
        self.cdefType = self.typedef.cType
        self.cReturnType = self.typedef.name + '*'
        self.overloadType = self.typedef.unscopedPyName

        if not self.inOut and (self.ptrCount == 2 or self.isRef and
                               self.isPtr):
            self.out = True

        if self.out or self.inOut:
            self.cType += '*'
            self.cdefType += '*'

        if self.array:
            self.cType += ' *'
            self.cdefType += '[]'
            self.overloadType = ('wrapper_lib.create_array_type(%s, ctype="%s")'
                                 % (self.typedef.name, self.cdefType))

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        if self.inOut:
            return """\
            {0}, {0}s_keepalive = {1.typedef.pyName}.py2c({0})
            {0}{2} = ffi.new('{1.cdefType}', {0})
            """.format(varName, self, OUT_PARAM_SUFFIX)
        if self.array:
            assert not inplace
            return ("{0}, {1}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2}, ctype='{3}').py2c({0})"
                    .format(varName, ARRAY_SIZE_PARAM, self.typedef.pyName,
                            self.cdefType))
        # XXX inplace is used only when making the lambda's for properties;
        #     maybe there's a better way to accomplish this?
        if inplace:
            return "{1}.py2c({0})[0]".format(varName, self.typedef.pyName)
        return "{0}, {0}s_keepalive = {1}.py2c({0})".format(varName,
                                                           self.typedef.pyName)

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        return varName

    def py2cPostcall(self, varName):
        return """\
        {0}, {0}s_keepalive = {1}.py2c({0})
        {0} = clib.{2}({0})
        """.format(varName, self.typedef.pyName, self.typedef.c2cppPyFunc)

    def c2py(self, varName):
        if self.out or self.inOut:
            return '%s.c2py(%s[0])' % (self.typedef.name, varName)
        if self.array:
            return ("wrapper_lib.create_array_type({2}, ctype='{3}').c2py({0}, {1})"
                    .format(varName, ARRAY_SIZE_PARAM, self.typedef.pyName,
                            self.cdefType))
        return '%s.c2py(%s)' % (self.typedef.name, varName)

    def c2cppPrecall(self, varName):
        if self.out:
            if self.isRef and self.ptrCount == 1 or self.ptrCount == 2:
                return '{0} *{1}_converted;'.format(self.typedef.name, varName)
            else:
                return '{0} {1}_converted;'.format(self.typedef.name, varName)
        if self.array:
            return "{0} {1}_converted = {2}({1}, {3});".format(
                self.cReturnType, varName, self.typedef.arrayc2cpp,
                ARRAY_SIZE_PARAM)

        deref = '*' if self.inOut else ''
        return '{0} {1}_converted = {2}({3}{1});'.format(
            self.cReturnType, varName, self.typedef.c2cppFunc, deref)

    def c2cppParam(self, varName):
        varName += '_converted'
        if self.array:
            return varName
        if self.out:
            if self.isRef:
                return varName
            else:
                return '&' + varName
        if self.inOut:
            if self.isRef:
                return '*' + varName
            else:
                return varName
        return ('*' if not self.isPtr else '') + varName

    def c2cppPostcall(self, varName):
        if self.array:
            return 'delete[] %s_converted;' % varName
        if self.inOut:
            return """\
            *{0} = {1}({0}_converted);
            delete {0}_converted;
            """.format(varName, self.typedef.cpp2cFunc)
        if self.out:
            return "*{0} = {1}({0}_converted);".format(varName,
                    self.typedef.cpp2cFunc)
        return 'delete %s_converted;' % varName

    def cpp2c(self, varName):
        if self.array:
            return "%s(%s, %s)" % (self.typedef.arraycpp2c, varName,
                                   ARRAY_SIZE_PARAM)
        return '%s(%s)' % (self.typedef.cpp2cFunc, varName)

class CharPtrTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(CharPtrTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.cType = 'char *'
        self.cdefType = 'char *'
        self.overloadType = '(unicode, str)'

        if self.isConst:
            self.cType = 'const char *'
            self.cdefType = 'const char *'

    def c2py(self, varName):
        return 'ffi.string(%s)' % varName

class BasicTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(BasicTypeInfo, self).__init__(typeName, typedef, **kwargs)
        if self.array:
            raise TypeError('use of the Array annotation is unsupported on '
                            "'%'parameters" % typeName)

        if self.pyInt and 'char' not in self.name:
            raise TypeError('use of the PyInt annotation is unsupported on '
                            "'%'parameters" % typeName)

        self.name = self.name.strip('*& ')
        self.cType = self.name
        self.cdefType = self.name
        self.cReturnType = self.cType

        if self.pyInt:
            self.cdefType = 'signed char'

        if self.isConst:
            self.cType = 'const ' + self.cType

        if self.name == 'bool' or isinstance(self.typedef, extractors.EnumDef):
            self.cType = 'int'
            self.cdefType = 'int'

        if (self.isPtr or self.isRef) and not self.inOut:
            self.out = True

        if self.out or self.inOut:
            self.cType += '*'
            self.cdefType += '*'

        self.overloadType = 'numbers.Number'
        if not self.pyInt and 'char' in self.name:
            self.overloadType = '(str, unicode)'

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        if self.inOut:
            return """\
            {0} = {1}({0})
            {0}{2} = ffi.new('{3}', {0})
            """.format(varName, BASIC_CTYPES[self.cdefType.strip('* ')],
                        OUT_PARAM_SUFFIX, self.cdefType)

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        # Use cdefType here to catch changes made by because PyInt
        return "%s(%s)" % (BASIC_CTYPES[self.cdefType], varName)

    def c2py(self, varName):
        if self.out or self.inOut:
            return varName + '[0]'
        return varName

    def c2cppParam(self, varName):
        if self.isRef:
            assert self.out or self.inOut
            return '*' + varName
        return varName
