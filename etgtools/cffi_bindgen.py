import os
import glob
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
BASIC_CTYPES = ('int', 'short', 'long', 'long long', 'float', 'double', 'char')

def load_module(self, module_name):
    pass

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
            #with open(os.path.join(DEF_DIR, mod + '.def'), 'rb') as f:
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

            # Print all Ctors
            for meth in klass:
                if (not isinstance(meth, extractors.MethodDef) or meth.ignored
                    or not meth.isCtor):
                    continue
                for m in meth.all():
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
        if overload == '':
            for i, m in enumerate(func.overloads):
                if m.ignored:
                    continue
                self.processFunction(m, '_%d' % i)
        func.pyImpl = []
        func.cppImpl = []
        if func.cppCode is not None and func.cppCode[1] == 'sip':
            # Don't actually do anything if this function has sip-specfic
            # custom code
            return

        func.cName = FUNC_PREFIX + func.name

        cArgs = self.createArgsString(func, parens=False, cTypes=True)
        cdefArgs = self.createArgsString(func, parens=False, voidPtrs=True,
                                         cTypes=True)
        cCallArgs = self.createArgsString(func, includeTypes=False,
                                          cTypes=True)

        cReturnType = func.type
        if cReturnType[-1] == '*':
            cdefReturnType = 'void *'
        else:
            cdefReturnType = cReturnType

        retStmt = 'return ' if func.type != 'void' else ''

        func.cdef = '%s %s(%s);' % (cdefReturnType, func.cName, cdefArgs)
        self.cdefs.append(func.cdef)

        if func.cppCode is None:
            func.cppImpl.append(nci("""\
            extern "C" %s %s(%s)
            {
                %s%s%s;
            }""" % (cReturnType, func.cName, cArgs,
                    retStmt, func.name, cCallArgs)))
        else:
            func.cppImpl.append(nci("""\
            extern "C" %s %s(%s)
            {""" % (cReturnType, func.cName, cArgs)))
            func.cppImpl.append(func.cppCode[0])
            func.cppImpl.append( "}")

    def processMethod(self, method, overload=''):
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
            cReturnType = method.klass.cppClassName + ' *'
        elif method.isDtor:
            cReturnType = 'void'
        else:
            cReturnType = method.type.replace('&', '*')

        if cReturnType[-1] == '*':
            cdefReturnType = 'void *'
        else:
            cdefReturnType = cReturnType


        if not method.isDtor:
            method.cName = '%s%s_88_%s%s' % (METHOD_PREFIX, method.klass.name, method.name, overload)
        else:
            method.cName = '%s%s_88_delete' % (METHOD_PREFIX, method.klass.name)

        cArgs = self.createArgsString(method, parens=False, cTypes=True)
        cppArgs = method.argsString.replace('=0', '')
        cdefArgs = self.createArgsString(method, parens=False, voidPtrs=True,
                                         cTypes=True)
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

        method.cdef = '%s %s(%s);' % (cdefReturnType, method.cName, cdefArgs)
        self.cdefs.append(method.cdef)

        method.cppImpl.append(nci("""\
        extern "C" %s %s(%s)
        {""" % (cReturnType, method.cName, cArgs)))

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

    def processParam(self, param):
        """
        Figure out what the appropriate C-type to use and whether we need to
        dereference it, and lookup if there is any conversion code.
        """
        if getattr(param, 'processed', False):
            return

        # Assume no special conversion
        param.pyConvertTo = param.cppConvertTo = None
        param.pyConvertFrom = param.cppConvertFrom = None

        typeName = param.type
        strippedType = (typeName.replace('::', '.').replace('const ', '')
                                .replace('unsigned ', '').strip(' *&'))
        typedef = self.findItem(strippedType) if strippedType != '' else None

        if typedef is None:
            if 'wxString' in typeName:
                param.cType = 'wxChar*'
                param.deref = False
            elif typeName in ('wxCoord', 'wxEventType', 'bool'):
                param.cType = 'int'
                param.deref = False
            elif typeName in BASIC_CTYPES or 'unsigned' in typeName:
                param.cType = param.type
                param.deref = False
            else:
                print "WARNING: unhandlable typedef", param.type
                # Until we have MappedTypes setup, treat this like a ClassDef
                if typeName[-1] == '*':
                    param.cType = typeName
                    param.deref = False
                elif typeName[-1] == '&':
                    param.cType = typeName.replace('&', '*')
                    param.deref =  True
                else:
                    param.cType = typeName + '*'
                    param.deref = True
        elif isinstance(typedef, extractors.EnumDef):
            param.cType = 'int'
            param.deref = False
        elif isinstance(typedef, extractors.ClassDef):
            # TODO: allow for MappedTypes?
            # for now enusre that we use pointers to handle all classes
            if typeName[-1] == '*':
                param.cType = typeName
                param.deref = False
            elif typeName[-1] == '&':
                param.cType = typeName.replace('&', '*')
                param.deref =  True
            else:
                param.cType = typeName + '*'
                param.deref = True
        elif isinstance(typedef, extractors.TypedefDef):
            original = param.type
            param.type = typedef.type
            self.processParam(param)
            param.type = original
        else:
            raise Exception('Unexpected typedef for a parameter type (%s)' %
                            param.type)

        param.processed = True

    def createArgsString(self, func, includeTypes=True, parens=True,
                              voidPtrs=False, cTypes=False):
        argsString = [] if not parens else ['(']
        for i, param in enumerate([i for i in func.items if not i.ignored]):
            if i != 0:
                argsString.append(', ')

            self.processParam(param)

            if includeTypes:
                if not cTypes:
                    type = param.type
                elif voidPtrs and param.cType[-1] == '*':
                    # TODO: we do not want to void a pointer if its a pointer
                    #       to a ctype (for example int*)
                    type = 'void *'
                else:
                    type = param.cType

                argsString.append(type)
                argsString.append(' ')
            elif cTypes and param.deref:
                argsString.append('*')

            argsString.append(param.name)

        if parens:
            argsString.append(')')
        return ''.join(argsString)

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
