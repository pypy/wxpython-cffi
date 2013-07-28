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
    'char': 'ffi.string',
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

    @classmethod
    def new(cls, typeName, findItem):
        if typeName not in cls._cache:
            typeInfo = TypeInfo(typeName, findItem)
            cls._cache[typeName] = typeInfo
            return typeInfo
        return cls._cache[typeName]

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

        methodMap = {
            extractors.ClassDef         : self.processClass,
            extractors.FunctionDef      : self.processFunction,
            extractors.CppMethodDef     : self.processCppMethod,
        }
        """
            extractors.DefineDef        : self.generateDefine,
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

        self.module.indent = 0
        for item in self.module:
            if item.ignored:
                continue
            if type(item) in methodMap:
                function = methodMap[type(item)]
                function(item)

        # TODO: sort items so that classes and global variables are defined
        #       by the time we need to reference them

    def write_files(self, pyfile, cppfile, verify_args=''):
        for attr in ('headerCode', 'cppCode', 'initializerCode',
                     'preInitializerCode', 'postInitializerCode'):
            for line in getattr(self.module, attr):
                print >> cppfile, line

        print >> pyfile, nci("""\
        import cffi
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
        self.writeItem(self.module, 0, pyfile, cppfile)

    def writeItem(self, item, indent,  pyfile, cppfile):
        for line in getattr(item, 'pyImpl', []):
            for l in line.splitlines():
                print >> pyfile, ' ' * indent + l
        for line in getattr(item, 'cppImpl', []):
            print >> cppfile, line
        for i in item:
            self.writeItem(i, indent + item.indent, pyfile, cppfile)

    def processClass(self, klass):
        klass.indent = 4
        klass.cppImpl = []
        klass.pyImpl = []

        virtualMethods = [i for i in klass
                            if isinstance(i, extractors.MethodDef)
                               and not i.isDtor and i.isVirtual
                               and not i.ignored]
        protectedMethods = [i for i in klass
                              if isinstance(i, extractors.MethodDef)
                                 and i.protection == 'protected'
                                 and not i.isVirtual and not i.ignored]

        dtor = klass.findItem('~' + klass.name)
        klass.hasVirtDtor = dtor is not None and not dtor.ignored and dtor.isVirtual
        klass.hasSubClass = (len(protectedMethods) > 0
                            or len(virtualMethods) > 0 or klass.hasVirtDtor)
        klass.cppClassName = (klass.name if not klass.hasSubClass
                                         else SUBCLASS_PREFIX + klass.name)

        ctors = [ctor for m in klass for ctor in m.all()
                      if isinstance(m, extractors.MethodDef) and m.isCtor and
                         not m.ignored]

        if klass.hasSubClass:
            # Create a subclass of the C++ type if we have any virtual or
            # protected methods
            klass.cppImpl.append(nci("""\
            class %(subClassName)s : public %(className)s
            {
            public:"""
            % {'className': klass.name, 'subClassName': klass.cppClassName}))

            # Process all Ctors
            for ctor in ctors:
                # Even though this function may actually return a pointer
                # to the subclass of the wrapped type, we'll use base class
                # as the return type so the TypeInfo code can be simpler
                method.type = method.klass.name + ' *'
                self.createArgsStrings(m)
                meth_def = "    %s %s%s;" % (m.type, klass.cppClassName,
                                                m.cppArgs)
                klass.cppImpl.append(meth_def)

            if klass.hasVirtDtor:
                klass.cppImpl.append("     virtual ~%s();" % klass.cppClassName)

            if len(virtualMethods) > 0:
                klass.cppImpl.append(nci("""\
                protected:
                    //Reimplement every virtual method"""))
            for vmeth in virtualMethods:
                for m in vmeth.all():
                    self.createArgsStrings(m)
                    meth_def = "    virtual %s %s%s;" % (m.type, m.name,
                                                         m.cppArgs)
                    klass.cppImpl.append(meth_def)

            if len(protectedMethods) > 0:
                klass.cppImpl.append(nci("""\
                public:
                    //Reimplement every protected method"""))
            for pmeth in protectedMethods:
                for m in pmeth.all():
                    self.createArgsStrings(m)
                    meth_def = "    %s unprotected_%s%s;" % (m.type, m.name,
                                                             m.cppArgs)
                    klass.cppImpl.append(meth_def)

            klass.cppImpl.append("};")

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
            __metaclass__ = wrapper_lib.wrapper_class(ffi, clib)"""
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
            if not type(item) in dispatch or item.ignored:
                continue
            item.klass = klass
            f = dispatch[type(item)]
            f(item)


    def processFunction(self, func, overload=''):
        assert not func.ignored
        # TODO: Add support for overloaded functions on the Python side
        if overload == '':
            for i, m in enumerate([m for m in func.overloads
                                     if not m.ignored]):
                self.processFunction(m, '_%d' % i)
        func.indent = 0
        func.pyImpl = []
        func.cppImpl = []

        self.getTypeInfo(func)
        self.createArgsStrings(func)

        if func.cppCode is not None and func.cppCode[1] == 'sip':
            # Don't actually do anything if this function has sip-specfic
            # custom code
            return

        func.cName = FUNC_PREFIX + func.name
        retStmt = 'return ' if func.type.name != 'void' else ''

        callName = func.name
        if func.cppCode is not None:
            callName = self.createCppCodeWrapper(func)

        func.cdef = '%s %s%s;' % (func.type.cdefType, func.cName,
                                  func.cdefArgs)
        self.cdefs.append(func.cdef)

        #if func.cppCode is None:
        func.cppImpl.append(nci("""\
        extern "C" %s %s%s
        {
            %s%s%s;
        }""" % (func.type.cType, func.cName, func.cArgs,
                retStmt, callName, func.cCallArgs)))

        func.pyImpl.append("def %s%s:" % (func.pyName, func.pyArgs))

        if func.type.name == 'void':
            func.pyImpl.append("    clib.%s%s" % (func.cName, func.pyCallArgs))
        else:
            func.pyImpl.append("    cdata = clib.%s%s" % (func.cName,
                               func.pyCallArgs))
            if func.type.isCBasic:
                func.pyImpl.append("    return %s(cdata)" %
                                   BASIC_CTYPES[func.type.cdefType])
            else:
                # If not a C basic, then it is a pointer to a wrapped type
                pass

    def processMethod(self, method, overload=''):
        assert not method.ignored
        if overload == '':
            for i, m in enumerate([m for m in method.overloads
                                     if not m.ignored]):
                m.klass = method.klass
                self.processMethod(m, '_%d' % i)

        method.indent = 0
        method.pyImpl = []
        method.cppImpl = []
        if method.cppCode is not None and method.cppCode[1] == 'sip':
            # Don't actually do anything if this method has sip-specfic
            # custom code
            return

        self.getTypeInfo(method)
        self.createArgsStrings(method)

        if method.isCtor:
            method.pyName = '__init__'

        if method.isDtor:
            # We need a special case for the dtor since '~' isn't allowed in an
            # function name
            method.cName = METHOD_PREFIX + method.klass.name + '_88_delete'
        else:
            method.cName = '%s%s_88_%s%s' % (METHOD_PREFIX, method.klass.name,
                                             method.name, overload)

        if method.cppCode is not None:
            callName = self.createCppCodeWrapper(method)
        elif method.protection == 'protected':
            callName = PROTECTED_PREFIX + method.name
        elif method.isStatic:
            callName = "%s::%s" % method.klass.name
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
            method.cppImpl.append('    ' + operation + callName +
                                  method.cCallArgs + ';')
        method.cppImpl.append('}')

        if (method.protection == 'protected' and not method.isDtor
            and not method.isCtor):
            method.cppImpl.append(nci("""\
            %s %s::%s%s
            {
                %s%s::%s%s;
            }""" % (method.type.name, method.klass.cppClassName, callName,
                    method.cppArgs, retStmt, method.klass.name, method.name,
                    method.cppCallArgs)))

        if method.isVirtual and not method.isDtor:
            # TODO: code to call python method
            method.cppImpl.append(nci("""\
            %s %s::%s%s
            {
                %s%s::%s%s;
            }
            """ % (method.type.name, method.klass.cppClassName, method.name,
                   method.dcppArgs, retStmt, method.klass.name, method.name,
                   method.cppCallArgs)))

        if method.isCtor:
            method.pyImpl.append(nci("""\
            def %s%s:
                cpp_obj = clib.%s%s
                import pdb; pdb.set_trace()
                wrapper_lib.CppWrapper.__init__(self, cpp_obj)
            """ % (method.pyName, method.pyArgs, method.cName,
                   method.pyCallArgs)))
        else:
            method.pyImpl.append(nci("""\
            def %s%s:
                return clib.%s%s
            """ % (method.pyName, method.pyArgs, method.cName,
                   method.pyCallArgs)))


    def processCppMethod(self, method):
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
            self.processMethod(method)
        else:
            self.processFunction(method)

    def processMemberVar(self, var):
        pass

    def processProperty(self, property):
        pass

    def processPyProperty(self, property):
        pass

    def processPyMethod(self, method):
        pass

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
            - `pyArgs`: Passed to the C function exposed via cffi
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
        func.pyArgs = []
        func.pyCallArgs = []
        func.cppArgs = []
        func.cppCallArgs = []

        if hasattr(func, 'klass') and not func.isStatic:
            func.pyArgs.append('self')
            if not func.isCtor:
                func.pyCallArgs.append('self._cpp_obj')
                func.cArgs.append('%s *self' % func.klass.cppClassName)
                func.cdefArgs.append('void *self')


        for param in [i for i in func.items if not i.ignored]:
            param.indent = 0
            self.getTypeInfo(param)

            cArg = "%s %s" % (param.type.cType, param.name)
            cdefArg = "%s %s" % (param.type.cdefType, param.name)
            cCallArg = "%s%s" % ('*' if param.type.deref else '', param.name)

            # XXX Maybe this should include const-ness too?
            cppArg = "%s %s" % (param.type.name, param.name)
            cppCallArg = "%s" % param.type.name

            pyArg = "%s%s%s" % (param.name, '=' if param.default else '',
                                defValueMap.get(param.default, param.default))
            pyCallArg = "%s" % param.name

            func.cArgs.append(cArg)
            func.cdefArgs.append(cdefArg)
            func.cCallArgs.append(cCallArg)
            func.cppArgs.append(cppArg)
            func.cppCallArgs.append(cppCallArg)

            # TODO: sometimes we don't want to include a parameter in pyArgs
            #       (like param.out == True for example)
            func.pyArgs.append(pyArg)
            if isinstance(param.type.typedef, extractors.ClassDef):
                func.pyCallArgs.append(pyArg + "._cpp_obj")
            else:
                func.pyCallArgs.append(pyArg)

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
        func.pyArgs = '(' + ', '.join(func.pyArgs) + ')'
        func.pyCallArgs = '(' + ', '.join(func.pyCallArgs) + ')'
        func.cppArgs = '(' + ', '.join(func.cppArgs) + ')'
        func.cppCallArgs = '(' + ', '.join(func.cppCallArgs) + ')'
        func.wrapperArgs = '(' + ', '.join(func.wrapperArgs) + ')'
        func.wrapperCallArgs = '(' + ', '.join(func.wrapperCallArgs) + ')'


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
        """ % (func.type.name, wrapperName, func.cppArgs)))
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
