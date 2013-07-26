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
BASIC_CTYPES = ('int', 'short', 'long', 'long long', 'float', 'double', 'char',
                'unsigned', 'void')

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
        # Additionally, references always need to be handled as pointers
        if isinstance(typedef, extractors.EnumDef):
            self.cType = 'int'
        elif isinstance(typedef, extractors.ClassDef):
            self.cType = typedef.name
        else:
            self.cType = typeName
        if self.isRef or self.isPtr or isinstance(typedef, extractors.ClassDef):
            self.cType += ' *'

        # Type for the cdef that will be called by cffi. Same rules as cType,
        # but must also treat all pointers to wrapped classes as `void *`
        if isinstance(typedef, extractors.EnumDef):
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

        # This is kind of a hack. We need to make sure that bools are handled
        # appropriately, but I'm not comfortable making a special case in
        # TypeInfo for them, so we'll simply make sure that a typedef for bool
        # is always available
        if self.findItem('bool') == None:
            self.module.addItem(extractors.TypedefDef(name='bool', type='int'))

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
        # TODO: figure out verify parameters

        for item in self.module:
            for line in getattr(item, 'pyImpl', []):
                print >> pyfile, line
            for line in getattr(item, 'cppImpl', []):
                print >> cppfile, line

    def processClass(self, klass):
        klass.cppClass = []
        klass.pyClass = []

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

        if klass.hasSubClass:
            # Create a subclass of the C++ type if we have any virtual or
            # protected methods
            klass.cppClass.append(nci("""\
            class %(subClassName)s : public %(className)s
            {
            public:"""
            % {'className': klass.name, 'subClassName': klass.cppClassName}))

            # Process all Ctors
            for meth in klass:
                if (not isinstance(meth, extractors.MethodDef) or meth.ignored
                    or not meth.isCtor):
                    continue
                for m in meth.all():
                    if m.ignored:
                        continue
                    argsString = self.createArgsString(m)
                    meth_def = "    %s %s%s;" % (m.type, klass.cppClassName,
                                                 argsString)
                    klass.cppClass.append(meth_def)

            if klass.hasVirtDtor:
                klass.cppClass.append("     virtual ~%s();" % klass.cppClassName)

            if len(virtualMethods) > 0:
                klass.cppClass.append(nci("""\
                protected:
                    //Reimplement every virtual method"""))
            for vmeth in virtualMethods:
                for m in vmeth.all():
                    argsString = self.createArgsString(m)
                    meth_def = "    virtual %s %s%s;" % (m.type, m.name,
                                                         argsString)
                    klass.cppClass.append(meth_def)

            if len(protectedMethods) > 0:
                klass.cppClass.append(nci("""\
                public:
                    //Reimplement every protected method"""))
            for pmeth in protectedMethods:
                for m in pmeth.all():
                    argsString = self.createArgsString(meth)
                    meth_def = "    %s unprotected_%s%s;" % (m.type, m.name,
                                                             argsString)
                    klass.cppClass.append(meth_def)

            klass.cppClass.append("};")


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
            for i, m in enumerate(func.overloads):
                if m.ignored:
                    continue
                self.processFunction(m, '_%d' % i)
        self.getTypeInfo(func)
        func.pyImpl = []
        func.cppImpl = []
        if func.cppCode is not None and func.cppCode[1] == 'sip':
            # Don't actually do anything if this function has sip-specfic
            # custom code
            return

        func.cName = FUNC_PREFIX + func.name

        cArgs = self.createArgsString(func, parens=False, cTypes=True)
        cdefArgs = self.createArgsString(func, parens=False, cdefTypes=True)
        cCallArgs = self.createArgsString(func, includeTypes=False,
                                          cTypes=True)

        retStmt = 'return ' if func.type.name != 'void' else ''

        func.cdef = '%s %s(%s);' % (func.type.cdefType, func.cName, cdefArgs)
        self.cdefs.append(func.cdef)

        if func.cppCode is None:
            func.cppImpl.append(nci("""\
            extern "C" %s %s(%s)
            {
                %s%s%s;
            }""" % (func.type.cType, func.cName, cArgs,
                    retStmt, func.name, cCallArgs)))
        else:
            func.cppImpl.append(nci("""\
            extern "C" %s %s(%s)
            {""" % (func.type.cType, func.cName, cArgs)))
            func.cppImpl.append(func.cppCode[0])
            func.cppImpl.append( "}")

        func.pyImpl.append("def %s(%s):" % (func.pyName, func.pyArgsString))

        if func.type == 'void':
            func.pyImpl.append("    clib.%s(%s)" % (func.cName, ''))
        else:
            func.pyImpl.append("    cdata = clib.%s(%s)" % (func.cName, ''))

    def processMethod(self, method, overload=''):
        assert not method.ignored
        if overload == '':
            for i, m in enumerate(method.overloads):
                if m.ignored:
                    continue
                m.klass = method.klass
                self.processMethod(m, '_%d' % i)
        method.pyImpl = []
        method.cppImpl = []
        if method.cppCode is not None and method.cppCode[1] == 'sip':
            # Don't actually do anything if this method has sip-specfic
            # custom code
            return

        if method.isCtor:
            # Even though this function may actually return a pointer to the
            # subclass of the wrapped type, we'll use base class as the return
            # type so the TypeInfo code can be simpler
            method.type = method.klass.name + ' *'
        self.getTypeInfo(method)

        if not method.isDtor:
            method.cName = '%s%s_88_%s%s' % (METHOD_PREFIX, method.klass.name, method.name, overload)
        else:
            method.cName = '%s%s_88_delete' % (METHOD_PREFIX, method.klass.name)

        cArgs = self.createArgsString(method, parens=False, cTypes=True)
        cppArgs = method.argsString.replace('=0', '')
        cdefArgs = self.createArgsString(method, parens=False, cdefTypes=True)
        cCallArgs = self.createArgsString(method, includeTypes=False,
                                          cTypes=True)
        cppCallArgs = self.createArgsString(method, includeTypes=False)

        if not method.isCtor and not method.isStatic:
            if len(cArgs) == 0:
                cArgs = method.klass.name + ' *self'
                cdefArgs = 'void *self'
            else:
                cArgs = method.klass.cppClassName + ' *self, ' + cArgs
                cdefArgs = 'void *self, ' + cdefArgs

        retStmt = 'return ' if method.type != 'void' else ''

        if not method.isStatic:
            callObj = 'self->'
        else:
            callObj = ''

        if method.protection == 'protected':
            callName = PROTECTED_PREFIX + method.name
        else:
            callName = method.name

        method.cdef = '%s %s(%s);' % (method.type.cdefType, method.cName,
                                      cdefArgs)
        self.cdefs.append(method.cdef)

        method.cppImpl.append(nci("""\
        extern "C" %s %s(%s)
        {""" % (method.type.cdefType, method.cName, cArgs)))

        # TODO: this if chain is wrong
        if method.cppCode is not None and method.cppCode[1] != 'sip':
            # Allow custom body code (ie a CppMethodDef)
            method.cppImpl.append(method.cppCode[0])
        elif method.isDtor:
            method.cppImpl.append('    delete self;')
        elif method.isCtor:
            method.cppImpl.append('    return new %s%s;'
                                  % (method.klass.cppClassName, cCallArgs))
        else:
            method.cppImpl.append('    %s%s%s%s;' % (retStmt, callObj,
                                                     callName, cCallArgs))
        method.cppImpl.append('}')

        if (method.protection == 'protected' and not method.isDtor
            and not method.isCtor):
            method.cppImpl.append(nci("""\
            %s %s::%s%s
            {
                %s%s::%s%s;
            }""" % (method.type, method.klass.cppClassName, callName, cppArgs,
                    retStmt, method.klass.name, method.name, cppCallArgs)))

        if method.isVirtual and not method.isDtor:
            # TODO: code to call python method
            method.cppImpl.append(nci("""\
            %s %s::%s%s
            {
                %s%s::%s%s;
            }
            """ % (method.type, method.klass.cppClassName, method.name, cppArgs,
                   retStmt, method.klass.name, method.name, cppCallArgs)))


    def processCppMethod(self, method):
        # Temporarily ignore methods if they are likely sip or CPython specific
        if 'sip' in method.body or 'Py' in method.body:
            return

        method.cppCode = (method.body, 'function')

        # CppMethodDefs have no ParamDefs, just an arg string. Build the list
        # of ParamDefs to make the CppMethodDefs more lke MethodDefs
        lastP = method.argsString.rfind(')')
        args = method.argsString[:lastP].strip('()').split(',')
        for arg in args:
            if not arg:
                continue
            # is there a default value?
            if '=' in arg:
                arg = arg.split('=')[0].strip()
            # Now the last word should be the variable name, and everything
            # before it is the type
            type, name = arg.rsplit(' ', 1)
            type = type.strip()
            method.items.append(extractors.ParamDef(name=name, type=type))

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

    def createArgsString(self, func, includeTypes=True, parens=True,
                              cdefTypes=False, cTypes=False):
        assert not cdefTypes or not cTypes

        args = []
        for param in [i for i in func.items if not i.ignored]:
            self.getTypeInfo(param)

            if includeTypes:
                if cTypes:
                    arg = param.type.cType
                elif cdefTypes:
                    arg = param.type.cdefType
                else: # C++ types
                    arg = param.type.name
                arg += ' '
            elif param.type.deref:
                arg = '*'
            else:
                arg = ''
            arg += param.name
            args.append(arg)

        argsString = ' ,'.join(args)
        if parens:
            argsString = '(%s)' % argsString
        return argsString

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
