from binascii import crc32

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
        self.__dict__.update(kwargs)

        if self.out and self.inOut or (self.out or self.inOut) and self.array:
            raise TypeError('invalid combination of anotations.')


    @classmethod
    def new(cls, typeName, findItem, **kwargs):
        typeName = typeName.strip()
        isRef = False
        isPtr = False
        isConst = False
        typedef = None

        name = typeName
        while True:
            isRef = (isRef or '&' in name)
            isPtr = (isPtr or '*' in name)
            isConst = (isConst or 'const ' in name)
            name = (name.replace('::', '.').replace('const ', '').strip(' *&'))
            typedef = findItem(name) if name != '' else None
            if isinstance(typedef, extractors.TypedefDef):
                name = typedef.type
            else:
                break

        if isinstance(typedef, extractors.ClassDef):
            type = WrappedTypeInfo
        elif isinstance(typedef, extractors.MappedTypeDef_cffi):
            type = MappedTypeInfo
        elif isPtr and 'char' in name:
            type = CharPtrTypeInfo
            typeName = name
        else:
            type = BasicTypeInfo
            typeName = name

        key = (typeName, frozenset(kwargs.items()))
        if key not in cls._cache:
            typeInfo = type(typeName, isRef=isRef, isPtr=isPtr,
                            isConst=isConst, typedef=typedef, **kwargs)
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

    def py2cPostcall(self, inVar, outVar):
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

    def virtualPreCallback(self, varName):
        return None

    def virtualPostCallback(self, varName):
        return None



class WrappedTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(WrappedTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.cType = self.typedef.unscopedName + ' *'
        self.cdefType = 'void *'
        self.cReturnType = self.typedef.name + ' *'
        self.cdefReturnType = 'void *'

        if self.isConst:
            self.cType = 'const ' + self.cType

        overloadTypes = [self.typedef.unscopedPyName]
        if hasattr(self.typedef, 'convertFromPyObject_cffi'):
            overloadTypes.append('{0}._pyobject_mapping_'.format(
                self.typedef.unscopedPyName))
        if self.isPtr or self.typedef.allowNone:
            overloadTypes.append('types.NoneType')
        self.overloadType = '(' + ', '.join(overloadTypes) + ')'

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

        self.cCbType = self.cType
        self.cdefCbType = self.cdefType

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        conversion = ''
        if hasattr(self.typedef, 'convertFromPyObject_cffi'):
            conversion = "{0} = {1}._pyobject_mapping_.convert({0})".format(
                varName, self.typedef.unscopedPyName)
        if self.inOut:
            return conversion + """\
            {0} = wrapper_lib.get_ptr({0})
            {0}{1} = ffi.new('{2}', {0})
            """.format(varName, OUT_PARAM_SUFFIX, self.cdefType)
        if self.array:
            return ("{0}, {1}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2}).py2c({0})"
                    .format(varName, ARRAY_SIZE_PARAM,
                            self.typedef.unscopedPyName, self.cdefType))
        return conversion if conversion != '' else None

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        if self.array:
            return varName
        return 'wrapper_lib.get_ptr(%s)' % varName

    def py2cPostcall(self, inVar, outVar):
        if self.out or self.inOut:
            return "%s[0] = wrapper_lib.get_ptr(%s)" % (outVar, inVar)
        return "%s = wrapper_lib.get_ptr(%s)" % (outVar, inVar)

    def c2py(self, varName):
        if self.out or self.inOut:
            # TODO: if this is * or &, make it py-owned, and if it is ** or
            #       *&, make it cpp-owned
            return 'wrapper_lib.obj_from_ptr(%s[0], %s)' % (
                    varName, self.typedef.unscopedPyName)
        if self.array:
            return ("wrapper_lib.create_array_type({2}).c2py({0}, {1})"
                    .format(varName, ARRAY_SIZE_PARAM,
                            self.typedef.unscopedPyName))
        if not (self.isRef or self.isPtr) or (not self.noCopy and
           self.isRef and self.isConst):
            return 'wrapper_lib.obj_from_ptr(%s, %s, True)' % (
                    varName, self.typedef.unscopedPyName)
        return 'wrapper_lib.obj_from_ptr(%s, %s)' % (
                varName, self.typedef.unscopedPyName)

    def cpp2c(self, varName):
        if self.array:
            return "%s(%s, %s)" % (self.typedef.arraycpp2c, varName,
                                   ARRAY_SIZE_PARAM)
        if self.out:
            if self.ptrCount == 2:
                return varName
            if  self.isRef and self.isPtr:
                return '&' + varName
            else:
                return '&' + varName + "_ptr"

        if self.inOut:
            return '&' + varName + "_ptr"
        # Always pass wrapped classes as pointers. If this is by value or
        # a const reference, it needs to be copy constructored onto the
        # heap, with Python taking ownership of the new object.
        if self.isPtr:
            return varName
        elif self.isRef and not self.isConst or self.noCopy:
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
        if self.array and not self.transfer:
            return 'delete[] %s_converted;' % varName
        return None

    def virtualPreCallback(self, varName):
        if self.array:
            return None

        if self.inOut or (self.out and self.ptrCount != 2 and not
                          (self.isRef and self.isPtr)):
            if self.isRef:
                initValue = '&' + varName
            elif self.isPtr:
                initValue = varName
            return "%s %s_ptr = %s;" % (self.cReturnType, varName, initValue)

    def virtualPostCallback(self, varName):
        if self.out or self.inOut:
            if self.ptrCount != 2 and not (self.isRef and self.isPtr):
                deref = '*' if self.isPtr else ''
                return """\
                if({1}_ptr != NULL)
                    {0}{1} = *{1}_ptr;""".format(deref, varName)

class MappedTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(MappedTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.cType = self.typedef.cType
        self.cdefType = self.typedef.cType
        self.cReturnType = self.typedef.name + '*'
        self.cdefReturnType = 'void *'

        overloadTypes = [self.typedef.unscopedPyName]
        if self.isPtr:
            overloadTypes.append('types.NoneType')
        self.overloadType = '(' + ', '.join(overloadTypes) + ')'

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

        if self.out:
            self.cCbType = self.typedef.name + '**'
            self.cdefCbType = "void **"
        else:
            self.cCbType = self.cType
            self.cdefCbType = self.cdefType

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        if self.inOut:
            return """\
            {0}, {0}s_keepalive = {1.typedef.unscopedPyName}.py2c({0})
            {0}{2} = ffi.new('{1.cdefType}', {0})
            """.format(varName, self, OUT_PARAM_SUFFIX)
        if self.array:
            assert not inplace
            return ("{0}, {1}, {0}_keepalive = "
                    "wrapper_lib.create_array_type({2}, ctype='{3}').py2c({0})"
                    .format(varName, ARRAY_SIZE_PARAM,
                            self.typedef.unscopedPyName, self.cdefType))
        # XXX inplace is used only when making the lambda's for properties;
        #     maybe there's a better way to accomplish this?
        if inplace:
            return "{1}.py2c({0})[0]".format(varName,
                                             self.typedef.unscopedPyName)
        return "{0}, {0}s_keepalive = {1}.py2c({0})".format(
            varName, self.typedef.unscopedPyName)

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        return varName

    def py2cPostcall(self, inVar, outVar):
        # inVar and outVar may both contain [x], so hash them to create a
        # usable temporary name
        tmpVar = "tmp_" + hex(crc32(inVar + outVar) & 0xffffffff)
        if self.out or self.inOut:
            return """\
            {2}, {2}_keepalive = {3}.py2c({0})
            {1}[0] = clib.{4}({2})
            """.format(inVar, outVar, tmpVar, self.typedef.unscopedPyName,
                   self.typedef.c2cppPyFunc)
        return """\
        {2}, {2}_keepalive = {3}.py2c({0})
        {1} = clib.{4}({2})
        """.format(inVar, outVar, tmpVar, self.typedef.unscopedPyName,
                self.typedef.c2cppPyFunc)

    def c2py(self, varName):
        if self.out or self.inOut:
            return '%s.c2py(%s[0])' % (self.typedef.unscopedPyName, varName)
        if self.array:
            return ("wrapper_lib.create_array_type({2}, ctype='{3}').c2py({0}, {1})"
                    .format(varName, ARRAY_SIZE_PARAM,
                            self.typedef.unscopedPyName, self.cdefType))
        return '%s.c2py(%s)' % (self.typedef.unscopedPyName, varName)

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
            if self.transfer:
                return None
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

        if self.out:
            if self.ptrCount == 2:
                return varName
            if  self.isRef and self.isPtr:
                return '&' + varName
            else:
                return '&' + varName + "_ptr"
        if self.inOut:
            return '&' + varName + "_converted"
        return '%s(%s)' % (self.typedef.cpp2cFunc, varName)

    def virtualPreCallback(self, varName):
        if self.out and self.ptrCount != 2 and not (self.isRef and self.isPtr):
            return "{0} {1}_ptr = NULL;".format(self.cReturnType, varName)
        if self.inOut:
            return """\
            union
            {{
                {0.cReturnType} {1}_ptr;
                {0.typedef.cType} {1}_converted;
            }};
            {1}_converted = {0.typedef.cpp2cFunc}({1});
            """.format(self, varName)
        return None

    def virtualPostCallback(self, varName):
        if self.out or self.inOut:
            if self.ptrCount != 2 and not (self.isRef and self.isPtr):
                deref = '*' if self.isPtr else ''
                return """\
                if({1}_ptr != NULL)
                    {0}{1} = *{1}_ptr;
                delete {1}_ptr;""".format(deref, varName)

class CharPtrTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(CharPtrTypeInfo, self).__init__(typeName, typedef, **kwargs)
        self.name = '%s *' % typeName
        if self.isConst:
            self.name = 'const ' + self.name

        self.cType = self.name
        self.cdefType = self.name
        self.overloadType = '(__builtin__.unicode, __builtin__.str)'
        self.cReturnType = self.name
        self.cdefReturnType = self.name

        self.cCbType = self.cType
        self.cdefCbType = self.cdefType

    def c2py(self, varName):
        return 'ffi.string(%s)' % varName

    def py2cPostcall(self, inVar, outVar):
        return "%s = wrapper_lib.allocate_cstring(%s, clib)" % (inVar, outVar)

class BasicTypeInfo(TypeInfo):
    def __init__(self, typeName, typedef, **kwargs):
        super(BasicTypeInfo, self).__init__(typeName, typedef, **kwargs)
        if self.array:
            raise TypeError('use of the Array annotation is unsupported on '
                            "'%'parameters" % typeName)

        if self.pyInt and 'char' not in self.name:
            raise TypeError('use of the PyInt annotation is unsupported on '
                            "'%'parameters" % typeName)

        self.cType = self.name.strip('*& ')
        self.cdefType = self.cType
        self.cReturnType = self.cType
        self.cdefReturnType = self.cType

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
            self.overloadType = '(__builtin__.str, __builtin__.unicode)'

        self.cCbType = self.cType
        self.cdefCbType = self.cdefType

    def lookupConversion(self):
        name = self.cdefType.strip('* ')
        if name in BASIC_CTYPES:
            return BASIC_CTYPES[name]

        if name.startswith('unsigned'):
            name = name[8:].strip(' ')
        if name.startswith('signed'):
            name = name[6:].strip(' ')
        return BASIC_CTYPES[name]

    def py2cPrecall(self, varName, inplace=False):
        if self.out:
            return "{0}{1} = ffi.new('{2}')".format(varName, OUT_PARAM_SUFFIX,
                                                      self.cdefType)
        if self.inOut:
            return """\
            {0} = {1}({0})
            {0}{2} = ffi.new('{3}', {0})
            """.format(varName, self.lookupConversion(),
                        OUT_PARAM_SUFFIX, self.cdefType)

    def py2cParam(self, varName):
        if self.out or self.inOut:
            return varName + OUT_PARAM_SUFFIX
        # Use cdefType here to catch changes made by because PyInt
        return "%s(%s)" % (self.lookupConversion(), varName)

    def py2cPostcall(self, inVar, outVar):
        if self.out or self.inOut:
            # For out and inOut cases, we're writing into a pointer
            return "%s[0] = %s(%s)" % (
                outVar, self.lookupConversion(), inVar)
        return "%s = %s(%s)" % (
            outVar, self.lookupConversion(), inVar)

    def c2py(self, varName):
        if self.out or self.inOut:
            return varName + '[0]'
        return varName

    def c2cppParam(self, varName):
        if self.isRef:
            assert self.out or self.inOut
            return '*' + varName
        return varName

    def cpp2c(self, varName):
        if self.isRef:
            return '&' + varName
        return varName
