import os
import glob
import types
import pickle
import cStringIO

import etgtools.extractors as extractors
import etgtools.generators as generators
from etgtools.generators import nci, Utf8EncodingStream, textfile_open, wrapText

from buildtools.config import Config
cfg = Config(noWxConfig=True)
DEF_DIR = os.path.join(cfg.ROOT_DIR, 'cffi', 'def_gen')

STATIC_MODULES = ('wxpy_api', 'arrayholder', 'filename', 'treeitemdata',
                  'wxpybuffer', 'arrays', 'longlong', 'userdata', 'clntdata',
                  'stockgdi', 'variant', 'dvcvariant', 'string', 'wxpy_api')

SUBCLASS_PREFIX = "cfficlass_"
PROTECTED_PREFIX = "unprotected_"
FUNC_PREFIX = "cffifunc_"
METHOD_PREFIX = "cffimeth_"
CPPCODE_WRAPPER_SUFIX = "_cppwrapper"

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
    'bool': 'bool',
    'void': None
}

class TypeInfo(object):
    _cache = {}
    def __init__(self, typeName, findItem):
        if typeName == '' or typeName is None:
            typeName = 'void'
        self.name = typeName
        self.isRef = False
        self.isPtr = False
        self.isConst = True

        # Loop until we find either a typedef that isn't a TypedefDef or we
        # find that their isn't any typedef for this type
        while True:
            self.isRef = (self.isRef or '&' in typeName)
            self.isPtr = (self.isPtr or '*' in typeName)
            typeName = (typeName.replace('::', '.').replace('const ', '')
                                .strip(' *&'))
            typedef = findItem(typeName) if typeName != '' else None
            if isinstance(typedef, extractors.TypedefDef):
                typeName = typedef.type
            else:
                break

        if not isinstance(typedef, (extractors.EnumDef, extractors.ClassDef,
                                    types.NoneType)):
            raise Exception("Unexpected typedef '%s' found for type '%s'" %
                            (str(type(typedef)), self.name))
        self.typedef = typedef

        # Note that typeName here is stripped of const, *, and &
        # `unsigned` is only a valid modifier on basic C types, so it stands to
        # reason that if its present this is a basic C type
        self.isCBasic = (typeName in BASIC_CTYPES or 'unsigned ' in typeName)

        if self.isCBasic == (self.typedef is not None):
            raise Exception("Type '%s' neither is a C basic type nor has a "
                             "typedef" % self.name)

        # Type for the extern "C" wrapper function. Needs to handle all wrapped
        # classes (classes with a ClassDef) as pointers and all enums as ints.
        # bools also need to be handled as ints since their actual size is an
        # implementation detail.  Additionally, references always need to be
        # handled as pointers.
        if isinstance(typedef, extractors.EnumDef) or typeName == 'bool':
            self.cType = 'int'
        elif isinstance(typedef, extractors.ClassDef):
            self.cType = typedef.name
        else:
            self.cType = typeName
        if self.isRef or self.isPtr or isinstance(typedef, extractors.ClassDef):
            self.cType += ' *'

        # Type for the cdef that will be called by cffi. Same rules as cType,
        # but must also treat all pointers to wrapped classes as `void *`
        if isinstance(typedef, extractors.EnumDef) or typeName == 'bool':
            self.cdefType = 'int'
        elif isinstance(typedef, extractors.ClassDef):
            self.cdefType = 'void'
        else:
            self.cdefType = typeName
        if self.isRef or self.isPtr or isinstance(self.typedef,
                                                  extractors.ClassDef):
            self.cdefType += ' *'

        # We need to dereference the pointer if our c type is a pointer but the
        # the type original type is not
        self.deref = self.cType[-1] == '*' and self.isPtr

        # TODO: Add the hook for MappedTypes here when adding them
        if self.isCBasic:
            if 'char' not in self.cType:
                # All of the c basics that not strings are numbers
                self.overloadType = 'numbers.Number'
            else:
                self.overloadType = '(str, unicode)'
        else:
            self.overloadType = self.typedef.pyName

    @classmethod
    def new(cls, typeName, findItem):
        if typeName not in cls._cache:
            typeInfo = TypeInfo(typeName, findItem)
            cls._cache[typeName] = typeInfo
            return typeInfo
        return cls._cache[typeName]

    def cpp2c(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            if not self.deref:
                # Always pass wrapped classes as pointers. Because any return
                # value that isn't a pointer will be temporary, it needs to bd
                # copy constructored into a heap variable.
                return "new %s(%s)" % (self.typedef.cppClassName, varName)
            else:
                return varName
        elif self.isCBasic:
            # C basic types don't need anything special
            return varName
        raise Exception()

    def c2py(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            return 'wrapper_lib.obj_from_ptr(%s, %s)' % (varName,
                                                         self.typedef.pyName)
        elif self.isCBasic:
            return varName
        raise Exception()

    def c2cpp(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            return ('*' if not self.deref else '') + varName
        elif self.isCBasic:
            return varName
        raise Exception()

    def py2c(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            return 'wrapper_lib.get_ptr(%s)' % varName
        elif self.isCBasic:
            return "%s(%s)" % (BASIC_CTYPES[self.cdefType], varName)
        raise Exception()

class MethodDefOverload(extractors.MethodDef):
    def __init__(self, original):
        self.__dict__ = original.__dict__

class CffiModuleGenerator(object):
    def __init__(self, module_name, path_pattern):
        with open(path_pattern % module_name, 'rb') as f:
            self.module = pickle.load(f)
        self.name = self.module.name
        self.completed = False

        for mod in self.module.includes:
            # We need to ignore the hand written sip modules for now
            if mod in STATIC_MODULES:
                continue
            with open(path_pattern % mod, 'rb') as f:
                mod = pickle.load(f)
                for attr in ('headerCode', 'cppCode', 'initializerCode',
                             'preInitializerCode', 'postInitializerCode',
                             'includes', 'imports', 'items'):
                    getattr(self.module, attr).extend(getattr(mod, attr))

    def generate(self, generators):
        if self.completed is True:
            return
        self.completed = True

        # Build a list of the generators for modules we're importing. We will
        # need this to lookup C++ classes that come from the imported modules
        self.module.imports = set(self.module.imports)
        self.imports = []
        for import_name in self.module.imports:
            self.imports.append(generators[import_name])
            generators[import_name].generate(generators)

        self.cdefs = []

        defaults = self.findDefaults(self.module)
        # TODO: findItem the defaults and get their pyNames

        methodMap = {
            extractors.ClassDef         : self.processClass,
            extractors.FunctionDef      : self.processFunction,
            extractors.CppMethodDef     : self.processCppMethod,
            MethodDefOverload           : self.processMethodOverload,
            extractors.DefineDef        : self.processDefine,
        }
        """
            extractors.EnumDef          : self.generateEnum,
            extractors.GlobalVarDef     : self.generateGlobalVar,
            extractors.TypedefDef       : self.generateTypedef,
            extractors.WigCode          : self.generateWigCode,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.PyFunctionDef    : self.generatePyFunction,
            extractors.PyClassDef       : self.generatePyClass,
            extractors.CppMethodDef_sip : self.generateCppMethod_sip,
            }
        """

        for item in self.module:
            if type(item) in methodMap:
                function = methodMap[type(item)]
                function(item, 0)

        # TODO: sort items so that classes and global variables are defined
        #       by the time we need to reference them

    def write_files(self, pyfile, cppfile, verify_args=''):
        for attr in ('headerCode', 'cppCode', 'initializerCode',
                     'preInitializerCode', 'postInitializerCode'):
            for line in getattr(self.module, attr):
                print >> cppfile, line

        print >> cppfile, "#include <cstring>"

        print >> pyfile, nci("""\
        import cffi
        import numbers
        import wrapper_lib""")

        for module in self.module.imports:
            print >> pyfile, "import %s" % module

        print >> pyfile, nci("""\
        ffi = cffi.FFI()
        cdefs = (
        """)

        for line in self.cdefs:
            print >> pyfile, "'''%s'''" % line
        print >> pyfile, nci("""\
        )
        ffi.cdef(cdefs)
        clib = ffi.verify(cdefs, %s)
        del cdefs""" % verify_args)
        self.writeItem(self.module, pyfile, cppfile)

    def writeItem(self, item, pyfile, cppfile):
        for line in getattr(item, 'pyImpl', []):
            print >> pyfile, line
        for line in getattr(item, 'cppImpl', []):
            print >> cppfile, line
        for i in item:
            self.writeItem(i, pyfile, cppfile)

    def findDefaults(self, item, defaults=set()):
        for i in item:
            if isinstance(i, extractors.ParamDef) and i.default != '':
                defaults.add(i.default)
            else:
                self.findDefaults(i, defaults)

        return defaults

    def processClass(self, klass, indent):
        assert not klass.ignored
        klass.cppImpl = []
        klass.pyImpl = []

        klass.type = klass.name + '*'
        self.getTypeInfo(klass)

        # Create a subclass of the C++ type if we have any virtual or
        # protected methods
        klass.hasSubClass = len([i for i in klass
                                   if isinstance(i, extractors.MethodDef) and
                                      (i.protection == 'protected' or
                                       i.isVirtual)]) > 0
        klass.cppClassName = (klass.name if not klass.hasSubClass
                                         else SUBCLASS_PREFIX + klass.name)

        # While we process the class's items, we'll build a list of the virtual
        # and protected methods' declarations to place in the subclass's body
        klass.virtualMethods = []
        klass.protectedMethods = []

        # In theory we should be able to just do `klass.findItem(klass.name is
        # not None` to check if a ctor exists, but there's no guarantee that a
        # ctor added by the tweaker will have its name set correctly
        ctors = [m for m in klass if isinstance(m, extractors.MethodDef) and
                                        m.isCtor]
        if len(ctors) == 0:
            # If the class doesn't have a ctor specified, we need to add a
            # default ctor
            klass.addItem(extractors.MethodDef(
                className=klass.name,
                name=klass.name,
                argsString='()',
                isCtor=True
            ))

        pyBases = ', '.join([b.pyName for b in klass.bases])
        if pyBases == '':
            pyBases = 'wrapper_lib.CppWrapper'
        if klass.pyName == '' or klass.pyName is None:
            klass.pyName = klass.name
        klass.pyImpl.append(nci("""\
        class %s(%s):
            __metaclass__ = wrapper_lib.WrapperType"""
        % (klass.pyName, pyBases)))


        dispatch = {
            extractors.MemberVarDef     : self.processMemberVar,
            extractors.PropertyDef      : self.processProperty,
            extractors.PyPropertyDef    : self.processPyProperty,
            extractors.MethodDef        : self.processMethod,
            #extractors.EnumDef          : self.processEnum,
            extractors.CppMethodDef     : self.processCppMethod,
            #extractors.CppMethodDef_sip : self.processCppMethod_sip,
            extractors.PyMethodDef      : self.processPyMethod,
            #extractors.PyCodeDef        : self.processPyCode,
            #extractors.WigCode          : self.processWigCode,
        }
        for item in klass:
            if not type(item) in dispatch:
                continue
            item.klass = klass
            f = dispatch[type(item)]
            f(item, indent + 4)


        if klass.hasSubClass:
            klass.cppImpl.append(nci("""\
            class {0} : public {1}
            {{
            public:""".format(klass.cppClassName, klass.name)))

            # Process all Ctors
            for ctor in ctors:
                meth_def = "    %s %s%s;" % (m.type, klass.cppClassName,
                                                m.cppArgs)
                klass.cppImpl.append(meth_def)

            # Signatures for re-implemented virtual methods
            if len(klass.virtualMethods) > 0:
                klass.cppImpl.append(nci("""\
                signed char vflags[%d];
                //Reimplement every virtual method"""
                % len(klass.virtualMethods), 4))
            for vmeth in klass.virtualMethods:
                    klass.cppImpl.append(vmeth)

            # Signatures for
            if len(klass.protectedMethods) > 0:
                klass.cppImpl.append(nci("""\
                    //Reimplement every protected method"""))
            for pmeth in klass.protectedMethods:
                klass.cppImpl.append(pmeth)

            klass.cppImpl.append("};")

            if len(klass.virtualMethods) > 0:
                vtableDef = 'void(*%s_vtable[%d])();' % (klass.name,
                                                        len(klass.virtualMethods))
                self.cdefs.append(vtableDef)
                self.cdefs.append('void %s_set_flag(void *, int);' %
                                  (klass.name))
                self.cdefs.append('void %s_set_flags(void *, char*);' %
                                   (klass.name))
                klass.cppImpl.append(nci("""\
                extern "C" {0}

                extern "C" void {1}_set_flag({2} * self, int i)
                {{
                    self->vflags[i] = 1;
                }}

                extern "C" void {1}_set_flags({2} * self, char * flags)
                {{
                    memcpy(self->vflags, flags, sizeof(self->vflags));
                }}
                """.format(vtableDef, klass.name, klass.cppClassName)))

                klass.pyImpl.append(nci("""\
                _vtable = clib.{0}_vtable

                def _set_vflag(self, i):
                    clib.{0}_set_flag(wrapper_lib.get_ptr(self), i)

                def _set_vflags(self, flags):
                    clib.{0}_set_flags(wrapper_lib.get_ptr(self), flags)
                """.format(klass.name), 4))



    def processFunction(self, func, indent, overload=''):
        assert not func.ignored

        func.pyImpl = []
        func.cppImpl = []
        self.getTypeInfo(func)
        self.createArgsStrings(func)

        if func.cppCode is not None and func.cppCode[1] == 'sip':
            # Don't actually do anything if this function has sip-specfic
            # custom code
            return

        func.cName = FUNC_PREFIX + func.name + overload
        func.retStmt = 'return ' if func.type.name != 'void' else ''

        # Figure out the name of the C++ function that we want to call from our
        # extern C wrapper. By default it is the C++ function we're wrapping,
        # but if we have custom code, it needs to be the name of the wrapper
        # where we're putting the custom code.
        callName = func.name
        if func.cppCode is not None:
            callName = self.createCppCodeWrapper(func)

        func.cdef = '%s %s%s;' % (func.type.cdefType, func.cName,
                                  func.cdefArgs)
        self.cdefs.append(func.cdef)

        func.cppImpl.append(nci("""\
        extern "C" {0.type.cType} {0.cName}{0.cArgs}
        {{
            {0.retStmt}{1}{0.cCallArgs};
        }}""".format(func, callName)))

        if func.hasOverloads():
            func.pyImpl.append(nci("""\
            @wrapper_lib.StaticMultimethod
            def %s():
                pass
            """ % func.pyName))

        if func.hasOverloads() or overload != '':
            func.pyImpl.append("@%s.overload%s" % (func.pyName, func.overloadArgs))
        func.pyImpl.append("def %s%s:" % (func.pyName, func.pyArgs))

        if func.type.name == 'void':
            func.pyImpl.append("    clib.%s%s" % (func.cName, func.pyCallArgs))
        else:
            func.pyImpl.append("    ret_value = " + func.type.c2py("clib.%s%s"
                               % (func.cName, func.pyCallArgs)))
            func.pyImpl.append("    return ret_value")

        for i, f in enumerate(func.overloads):
            self.processFunction(f, indent, '_%d' % i)
            func.pyImpl.extend(f.pyImpl)
            func.cppImpl.extend(f.cppImpl)
        self.overloads = []

    def processMethod(self, method, indent, overload=''):
        assert not method.ignored
        if method.hasOverloads():
            # Move The bodies of the overloaded methods are outside of the
            # class body and place them at the end of the module to ensure that
            # every type they need has been defined already. Trying to sort
            # classes so that every dependency has already been defined can't
            # work because of methods like copy constructors which reference
            # the class they are defined in.
            method.klass.items[method.klass.items.index(method)] = extractors.BaseDef()
            self.module.items.append(MethodDefOverload(method))
            for i, m in enumerate(method.overloads):
                m.klass = method.klass
                m.overloadId = '_%d' % i
                self.module.items.append(MethodDefOverload(m))
            m.closeMM = True
            self.processOverloadBase(method, indent)
            method.overloadId = ''
            method.overloads = []
            return

        method.pyImpl = []
        method.cppImpl = []
        if method.cppCode is not None and method.cppCode[1] == 'sip':
            # Don't actually do anything if this method has sip-specfic
            # custom code
            return

        # Even though this method may actually return a pointer to the
        # subclass of the wrapped type, we'll use base class as the return type
        # so the TypeInfo code can be simpler
        method.type = method.klass.name + '*' if method.isCtor else method.type
        method.pyName = '__init__' if method.isCtor else method.pyName

        self.getTypeInfo(method)
        self.createArgsStrings(method)

        method.retStmt = 'return ' if method.type.name != 'void' else ''

        if method.isDtor:
            # We need a special case for the dtor since '~' isn't allowed in an
            # function name
            method.pyName = '__del__'
            method.cName = METHOD_PREFIX + method.klass.name + '_88_delete'
        else:
            method.cName = '%s%s_88_%s%s' % (METHOD_PREFIX, method.klass.name,
                                             method.name, overload)

        if method.isVirtual:
            self.processVirtualMethod(method, indent, overload)

        callArgs = method.cCallArgs
        if method.cppCode is not None:
            callName = self.createCppCodeWrapper(method)
            callArgs = method.wrapperCallArgs
        elif method.protection == 'protected':
            # We only need to do the special handling of a protected method if
            # it has not custom code.
            callName = self.processProtectedMethod(method, indent, overload)
        elif method.isStatic:
            callName = "%s::%s" % (method.klass.name, method.name)
        elif method.isCtor:
            callName = method.klass.cppClassName
        else:
            # Just in case, we'll always specify the original implementation,
            # for both regular and virtual methods
            callName = "self->%s::%s" % (method.klass.name, method.name)

        method.cdef = '%s %s%s;' % (method.type.cdefType, method.cName,
                                      method.cdefArgs)
        self.cdefs.append(method.cdef)

        operation = 'return ' if method.type.name != 'void' else ''
        operation += 'new ' if method.isCtor else ''


        method.cppImpl.append(nci("""\
        extern "C" %s %s%s
        {""" % (method.type.cdefType, method.cName, method.cArgs)))
        if method.isDtor:
            method.cppImpl.append('    delete self;')
        else:
            method.cppImpl.append('    ' + operation + method.type.cpp2c(callName +
                                  callArgs) + ';')
        method.cppImpl.append('}')


        if method.isStatic and not method.hasOverloads() and overload == '':
            method.pyImpl.append(nci("@staticmethod", indent))
        call = 'clib.{0.cName}{0.pyCallArgs}'.format(method)
        if method.isCtor:
            method.pyImpl.append(nci("""\
            def __init__{0.pyArgs}:
                cpp_obj = {1}
                wrapper_lib.CppWrapper.__init__(self, cpp_obj)
            """.format(method, call), indent))
        else:
            method.pyImpl.append(nci("""\
            def {0.pyName}{0.pyArgs}:
                return {1}
            """.format(method, method.type.c2py(call)), indent))

    def processVirtualMethod(self, method, indent, overload=''):
        if method.isDtor:
            return
        meth_def = "    virtual {0.type.name} {0.name}{0.cppArgs};".format(
                    method)
        method.klass.virtualMethods.append(meth_def)
        index = len(method.klass.virtualMethods) - 1

        funcPtrName = '%s_%s_FUNCPTR' % (method.klass.name, index)
        cbCall = '(({0}){1.klass.name}_vtable[{2}]){1.cbCallArgs}'.format(
                  funcPtrName, method, index)

        method.cppImpl.append(nci("""\
        extern "C" typedef {0.type.cType} (*{1}){0.cArgs};
        {0.type.name} {0.klass.cppClassName}::{0.name}{0.cppArgs}
        {{
            if(this->vflags[{2}])
                {0.retStmt}{3};
            else
                {0.retStmt}{0.klass.name}::{0.name}{0.cppCallArgs};
        }}""".format(method, funcPtrName, index, method.type.c2cpp(cbCall))))

        call = '{0}.{1.pyName}{1.vtdCallArgs}'.format(
                method.klass.type.c2py('self'), method)
        method.pyImpl.append(nci("""\
        @wrapper_lib.VirtualDispatcher({0})
        @ffi.callback('{1.type.cdefType}(*){1.cdefArgs}')
        def _virtual__{0}{1.vtdArgs}:
            return {2}
        """.format(index, method, method.type.py2c(call)), indent))

        method.pyImpl.append(nci("@wrapper_lib.VirtualMethod(%d)" %
                                 (len(method.klass.virtualMethods) - 1),
                                  indent))

    def processProtectedMethod(self, method, indent, overload=''):
        if method.isCtor:
            # We don't need any special code for protected ctors; they're
            # already exposed when we create a new ctor that call the old one
            return
        callName = PROTECTED_PREFIX + method.name
        meth_def = "    {0.type.name} unprotected_{0.name}{0.cppArgs};".format(method)
        method.klass.protectedMethods.append(meth_def)
        method.cppImpl.append(nci("""\
        {0.type.name} {0.klass.cppClassName}::{1}{0.cppArgs}
        {{
            {0.retStmt}{0.klass.name}::{0.name}{0.cppCallArgs};
        }}""".format(method, callName)))

        return "self->" + callName


    def processCppMethod(self, method, indent):
        assert not method.ignored
        # Temporarily ignore methods if they are likely sip or CPython specific
        if 'sip' in method.body or 'Py' in method.body:
            return

        method.cppCode = (method.body, 'function')

        # CppMethodDefs have no ParamDefs, just an arg string. Build the list
        # of ParamDefs to make the CppMethodDefs more lke FunctionDefs
        method.items = self.disassembleArgsString(method.argsString)

        # Some CppMethodDefs are not inside classes, but are global functions
        # instead.
        if hasattr(method, 'klass') and method.klass is not None:
            self.processMethod(method, indent)
        else:
            self.processFunction(method, indent)

    def processOverloadBase(self, method, indent):
        if method.isCtor:
            method.pyName = '__init__'
        mmType = '' if not method.isStatic else 'Static'
        method.klass.pyImpl.append(nci("""\
        @wrapper_lib.{1}Multimethod
        def {0.pyName}():
            #TODO: docstring here
            pass
        """.format(method, mmType), indent))

    def processMethodOverload(self, method, indent):
        self.processMethod(method, indent, method.overloadId)
        self.cppImpl = []
        method.pyImpl = [nci("""\
        @{0.klass.pyName}.{0.pyName}.overload{0.overloadArgs}
        """.format(method), indent)] + method.pyImpl

        if hasattr(method, 'closeMM'):
            method.pyImpl.append(nci("""\
            {0.klass.pyName}.{0.pyName}.finish()
            """.format(method), indent))

    def processMemberVar(self, var):
        assert not method.ignored
        pass

    def processProperty(self, property):
        assert not method.ignored
        pass

    def processPyProperty(self, property):
        assert not method.ignored
        pass

    def processPyMethod(self, method):
        assert not method.ignored
        pass

    def processDefine(self, define, indent):
        assert not define.ignored
        define.pyImpl = []
        define.cppImpl = []

        cName = "cffidefine_" + define.name
        # Let's assume that defines are always integers for now.
        self.cdefs.append("extern const int %s;" % cName)
        define.pyImpl.append("%s = clib.%s" %
                             (define.pyName, cName))
        define.cppImpl.append("""extern "C" const int %s = %s;""" %
                              (cName, define.name))

    def getTypeInfo(self, item):
        if isinstance(item.type, (str, types.NoneType)):
            item.type = TypeInfo(item.type, self.findItem)

    def createArgsStrings(self, func):
        """
        Functions need 5 or 7 different args strings:
            - `cArgs`: For the extern "C" function
            - `cdefArgs`: Passed to ffi.cdef
            - `cCallArgs`: Passed to the wrapping function; has dereferences
                          where necessary
            - `pyArgs`: For the definition of the Python function; includes
                        default values
            - `pyCallArgs`: Passed to the C function exposed via cffi
            - `cppArgs`: Only for virtual or protected method or function with
                         cppCode set. Used in the signature of the extra method
                         needed in those situations
            - `cppCallArgs`: Only for virtual or protected method or function
                             with cppCode set. Used inside extra method need
                             in those situations
        For simplicity's sake, we'll create all 7 in anyway case
        """
        if hasattr(func, 'cArgs'):
            # This function has had its args strings created
            return

        # XXX Should this be a global? It'd certainly be more visible
        defValueMap = {
            'true':  'True',
            'false': 'False',
            'NULL':  'None',
            'wxString()': '""',
            'wxArrayString()' : '[]',
            'wxArrayInt()' : '[]',
        }

        func.cArgs = []
        func.cdefArgs = []
        func.cCallArgs = []
        func.cbCallArgs = []
        func.vCallArgs = []
        func.pyArgs = []
        func.pyCallArgs = []
        func.vtdArgs = []
        func.vtdCallArgs = []
        func.cppArgs = []
        func.cppCallArgs = []
        func.overloadArgs = []

        if hasattr(func, 'klass') and not func.isStatic:
            func.pyArgs.append('self')
            if not func.isCtor:
                func.pyCallArgs.append('wrapper_lib.get_ptr(self)')
                func.cArgs.append('%s *self' % func.klass.cppClassName)
                func.cdefArgs.append('void *self')
                func.cbCallArgs.append('this')
                func.vtdArgs.append('self')


        for param in func.items:
            self.getTypeInfo(param)

            cArg = "%s %s" % (param.type.cType, param.name)
            cdefArg = "%s %s" % (param.type.cdefType, param.name)
            cCallArg = param.type.c2cpp(param.name)
            cbCallArg = param.type.cpp2c(param.name)

            cppArg = "%s%s %s" % ('const ' if param.type.isConst else '',
                                  param.type.name, param.name)
            cppCallArg = "%s" % param.name

            pyArg = "%s%s%s" % (param.name, '=' if param.default else '',
                                defValueMap.get(param.default, param.default))
            pyCallArg = param.type.py2c(param.name)
            vtdArg = param.name
            vtdCallArg = param.type.c2py(param.name)
            overloadArg = param.name + '=' + param.type.overloadType

            func.cArgs.append(cArg)
            func.cdefArgs.append(cdefArg)
            func.cCallArgs.append(cCallArg)
            func.cbCallArgs.append(cbCallArg)
            func.cppArgs.append(cppArg)
            func.cppCallArgs.append(cppCallArg)
            func.pyArgs.append(pyArg)
            func.pyCallArgs.append(pyCallArg)
            func.vtdArgs.append(vtdArg)
            func.vtdCallArgs.append(vtdCallArg)
            func.overloadArgs.append(overloadArg)

        # We're generating a wrapper function that needs a `self` pointer in
        # its args string if this function has custom C++ code or is protected
        # and not static
        if hasattr(func, 'klass') and (func.cppCode is not None or
           (func.protection == 'protected' and not func.isStatic)):
            func.wrapperArgs = (['%s *self' % func.klass.cppClassName] +
                                func.cppArgs)
            func.wrapperCallArgs = ['self'] + func.cppCallArgs
        else:
            func.wrapperArgs = []
            func.wrapperCallArgs = []

        func.cArgs = '(' + ', '.join(func.cArgs) + ')'
        func.cdefArgs = '(' + ', '.join(func.cdefArgs) + ')'
        func.cCallArgs = '(' + ', '.join(func.cCallArgs) + ')'
        func.cbCallArgs = '(' + ', '.join(func.cbCallArgs) + ')'
        func.pyArgs = '(' + ', '.join(func.pyArgs) + ')'
        func.pyCallArgs = '(' + ', '.join(func.pyCallArgs) + ')'
        func.cppArgs = '(' + ', '.join(func.cppArgs) + ')'
        func.cppCallArgs = '(' + ', '.join(func.cppCallArgs) + ')'
        func.vtdArgs = '(' + ', '.join(func.vtdArgs) + ')'
        func.vtdCallArgs = '(' + ', '.join(func.vtdCallArgs) + ')'
        func.wrapperArgs = '(' + ', '.join(func.wrapperArgs) + ')'
        func.wrapperCallArgs = '(' + ', '.join(func.wrapperCallArgs) + ')'
        func.overloadArgs = '(' + ', '.join(func.overloadArgs) + ')'


    def disassembleArgsString(self, argsString):
        """
        CppMethodDefs are always specified with an empty parameter list. So we
        can treat them like regular FunctionDefs where ever possible, we'll use
        this method to disassemble their args string into a list of ParamDefs.
        Based loosely on the extractors.FunctionDef.makePyArgsString
        """
        # XXX This really doesn't need to be a method. Maybe make it a global
        #     function later?
        # TODO: This may also be used for cppSignature when we get around it
        params = []
        args = argsString.rsplit(')')[0].strip('(').split(',')
        for arg in args:
            if not arg:
                continue
            param = extractors.ParamDef()
            # Is there a default value?
            if '=' in arg:
                param.default = arg.split('=')[1].strip()
                arg = arg.split('=')[0].strip()
            # Now the last word should be the variable name, and everything
            # before it is the type
            param.type, param.name = arg.rsplit(' ', 1)[-1]
            params.append(arg)

        return params

    def createCppCodeWrapper(self, func):
        """
        To handle custom code on C++ we need to create an extra function to
        wrap the custom code. This new function is then what's called by the
        extern "C" function. Part of the reason this is necessary is because
        the custom code expects to deal with the original C++ types of the
        function and not the types the extern "C" function uses.
        """
        wrapperName = func.cName + CPPCODE_WRAPPER_SUFIX
        func.cppImpl.append(nci("""\
        %s %s%s
        {
        """ % (func.type.name, wrapperName, func.wrapperArgs)))
        func.cppImpl.append(func.cppCode)
        func.cppImpl.append("}")

        return wrapperName

    def findItem(self, name):
        item = self.module.findItem(name)
        if item is not None:
            return item

        for gen in self.imports:
            item = gen.findItem(name)
            if item is not None:
                return item

        return None


if __name__ == '__main__':
    generators = {}
    path_pattern = os.path.join(DEF_DIR, '%s.def')
    def_glob =  path_pattern % '_*'
    for mod_path in glob.iglob(def_glob):
        mod_name = os.path.splitext(os.path.basename(mod_path))[0]
        gen = CffiModuleGenerator(mod_name, path_pattern)
        generators[gen.name] = gen

    for gen in generators.values():
        gen.generate(generators)
        pyfile = cStringIO.StringIO()
        cppfile = cStringIO.StringIO()
        gen.write_files(pyfile, cppfile)
