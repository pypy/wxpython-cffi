import re
import os
import sys
import glob
import types
import pickle
import cStringIO

import etgtools.extractors as extractors
import etgtools.generators as generators
from etgtools.generators import nci, Utf8EncodingStream, textfile_open, wrapText
from etgtools.tweaker_tools import magicMethods

from etgtools.cffi_typeinfo import (
    ARRAY_SIZE_PARAM, OUT_PARAM_SUFFIX, TypeInfo, WrappedTypeInfo,
    MappedTypeInfo, CharPtrTypeInfo, BasicTypeInfo)

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
DEFINE_PREFIX = "cffidefine_"
MEMBER_VAR_PREFIX = "cffimvar_"
GLOBAL_VAR_PREFIX = "cffigvar_"
ENUM_PREFIX = "cffienum_"
CONVERT_PREFIX = "cfficonvert_"
CPPCODE_WRAPPER_SUFIX = "_cppwrapper"

def categorize(list, *types):
    categories = tuple([] for i in range(len(types) + 1))
    for obj in list:
        for i, type in enumerate(types):
            if isinstance(obj, type):
                categories[i].append(obj)
                break
        else:
            categories[-1].append(obj)

    return categories

def dispatchItems(methodMap, items, *args, **kwargs):
    i = 0
    while i < len(items):
        item = items[i]
        i += 1
        if type(item) in methodMap:
            function = methodMap[type(item)]
            function(item, *args, **kwargs)

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
        TypeInfo.clearCache()

        self.dispatchInit = {
            extractors.FunctionDef      : self.initFunction,
            extractors.CppMethodDef     : self.initCppMethod,
            extractors.GlobalVarDef     : self.initGlobalVar,
            extractors.EnumDef          : self.initEnum,
            extractors.DefineDef        : self.initDefine,
        }
        self.dispatchClassItemInit = {
            extractors.MemberVarDef     : self.initMemberVar,
            extractors.MethodDef        : self.initMethod,
            extractors.CppMethodDef     : self.initCppMethod,
            extractors.EnumDef          : self.initEnum,
        }
        self.dispatchCDefs = {
            extractors.FunctionDef      : self.printFunctionCDef,
            extractors.CppMethodDef     : self.printCppMethodCDef,
            extractors.DefineDef        : self.printDefineCDef,
            extractors.GlobalVarDef     : self.printGlobalVarCDef,
            extractors.EnumDef          : self.printEnumCDef,
        }
        self.dispatchClassItemCDefs = {
            extractors.MemberVarDef     : self.printMemberVarCDef,
            extractors.MethodDef        : self.printMethodCDef,
            extractors.CppMethodDef     : self.printCppMethodCDef,
            extractors.EnumDef          : self.printEnumCDef,
        }
        self.dispatchPrint = {
            extractors.FunctionDef          : self.printFunction,
            extractors.CppMethodDef         : self.printCppMethod,
            extractors.DefineDef            : self.printDefine,
            extractors.GlobalVarDef         : self.printGlobalVar,
            extractors.EnumDef              : self.printEnum,
            extractors.EnumDef              : self.printEnum,
        }
        self.dispatchClassItemPrint = {
            extractors.MemberVarDef     : self.printMemberVar,
            extractors.MethodDef        : self.printMethod,
            extractors.CppMethodDef     : self.printCppMethod,
            extractors.EnumDef          : self.printEnum,
            extractors.PropertyDef      : self.printProperty,
        }
        self.dispatchFinalize = {
            extractors.FunctionDef      : self.printFunctionFinalization,
            extractors.CppMethodDef     : self.printCppMethodFinalization,
        }
        self.dispatchPrintPyDefs = {
            extractors.PyClassDef       : self.printPyClass,
            extractors.PyCodeDef        : self.printPyCode,
            extractors.PyFunctionDef    : self.printPyFunction,
        }
        self.dispatchPrintClassPyDefs = {
            extractors.PyCodeDef        : self.printPyCode,
            extractors.PyPropertyDef    : self.printPyProperty,
            extractors.PyMethodDef      : self.printPyMethod,
        }
        self.dispatchPrintPyClassItems = {
            extractors.PyFunctionDef    : self.printPyFunction,
            extractors.PyPropertyDef    : self.printPyProperty,
            extractors.PyCodeDef        : self.printPyCode,
            extractors.PyClassDef       : self.printPyClass,
        }


    def init(self, generators):
        if self.completed is True:
            return
        self.completed = True

        # Build a list of the generators for modules we're importing. We will
        # need this to lookup C++ classes that come from the imported modules
        self.module.imports = set(self.module.imports)
        self.imports = []
        for import_name in self.module.imports:
            self.imports.append(generators[import_name])
            generators[import_name].init(generators)

        # Move all global Py*Defs and classes into seperate lists
        pydefTypes = (extractors.PyClassDef, extractors.PyCodeDef,
                      extractors.PyFunctionDef)
        categories = categorize(self.module.items, pydefTypes,
                                extractors.ClassDef,
                                extractors.MappedTypeDef_cffi)
        self.pyItems, self.classes, self.mappedTypes, self.globalItems = categories

        self.pyItems.sort(key=lambda item: item.order if item.order is not None
                                                      else sys.maxint)

        for klass in self.classes:
            self.initClass(klass)
        self.sortClasses()

        for mType in self.mappedTypes:
            self.initMappedType(mType)

        for klass in self.classes:
            self.initClassItems(klass)
        dispatchItems(self.dispatchInit, self.globalItems)


    # TODO: some of the C++ code needs to written to a seperate header file so
    #       that other modules can access this modules declarations
    def writeFiles(self, pyfile, cppfile, verify_args=''):
        # Write the C++ preamble
        print >> cppfile, "#include <cstring>"
        print >> cppfile, "#include <wrapper_lib.h>"
        for attr in ('headerCode', 'cppCode', 'initializerCode',
                     'preInitializerCode', 'postInitializerCode'):
            for line in getattr(self.module, attr):
                print >> cppfile, line

        for item in self.module.items:
            for line in  getattr(item, 'headerCode', []):
                print >> cppfile, line

        # Write Python preamble
        print >> pyfile, nci("""\
        import cffi
        import types
        import numbers
        import wrapper_lib""")
        for module in self.module.imports:
            print >> pyfile, "import %s" % module

        # Write cdefs
        print >> pyfile, nci("""\
        ffi = cffi.FFI()
        cdefs = ('''
        void* malloc(size_t);
        void free(void*);""")
        for klass in self.classes:
            self.printClassCDefs(klass, pyfile)
        for mType in self.mappedTypes:
            self.printMappedTypeCDef(mType, pyfile)
        dispatchItems(self.dispatchCDefs, self.globalItems, pyfile)
        print >> pyfile, nci("""\
        ''')
        ffi.cdef(cdefs)
        clib = ffi.verify(cdefs, %s)
        del cdefs""" % verify_args)

        # Print classes' C++ bodies, before any method bodies are printed
        for klass in self.classes:
            self.printClassCppBody(klass, cppfile)

        for mType in self.mappedTypes:
            self.printMappedType(mType, pyfile, cppfile, 0)

        # Print classes' Python bodies and items
        for klass in self.classes:
            self.printClass(klass, pyfile, cppfile)

        # Print global items
        dispatchItems(self.dispatchPrint, self.globalItems, pyfile, cppfile)

        # Print Python finalization code (finalize multimethods, etc)
        for klass in self.classes:
            self.printClassFinalization(klass, pyfile)
        dispatchItems(self.dispatchFinalize, self.globalItems, pyfile)

        # Print Py*Defs
        for klass in self.classes:
            self.printClassPyDefs(klass, pyfile)
        dispatchItems(self.dispatchPrintPyDefs, self.pyItems, pyfile, 0)

    def sortClasses(self):
        """
        Sort clases so that all of a given classes bases occur before it
        """
        def getDependencies(klass):
            dependencies = []
            for baseName in klass.bases:
                baseDef = self.findItem(baseName)
                if isinstance(baseDef, extractors.ClassDef):
                    dependencies.append(baseDef)
                else:
                    raise Exception("Failed to locate a ClassDef for base '%s'"
                                    " for class '%s'" % (klass.name, baseName))
            for ic in klass.innerclasses:
                dependencies.extend(getDependencies(ic))
            return dependencies

        # Map items to items that depend on them
        dependents = {}
        finalClassOrder = []
        for klass in self.classes:
            deps = getDependencies(klass)
            if len(deps) == 0:
                finalClassOrder.append(klass)
            else:
                klass.deps = set(deps)
                for d in deps:
                    if d not in dependents:
                        assert isinstance(d, extractors.ClassDef)
                        dependents[d] = set()
                    dependents[d].add(klass)

        i = 0
        while i < len(finalClassOrder):
            item = finalClassOrder[i]
            i += 1
            items = [item] + getattr(item, 'innerclasses', [])
            for dependency in items:
                if dependency in dependents:
                    dependentItems = dependents[dependency]
                    del dependents[dependency]
                    for dependentItem in dependentItems:
                        dependentItem.deps.remove(dependency)
                        if len(dependentItem.deps) == 0:
                            finalClassOrder.append(dependentItem)

        assert set(finalClassOrder) == set(self.classes)
        assert len(finalClassOrder) == len(self.classes)
        self.classes == finalClassOrder

    def initClass(self, klass):
        assert not klass.ignored

        if not hasattr(klass, 'klass'):
            klass.unscopedName = klass.name
            klass.pyName = klass.pyName or klass.name
            klass.unscopedPyName = klass.pyName

            klass.cName = klass.name
        else:
            klass.cName = klass.klass.name + '_88_' + klass.name

        klass.briefDoc = klass.briefDoc if klass.briefDoc is not None else ''

        klass.arrayc2cpp = "cfficonvert_wrappedtype_c2cpp_array"
        klass.arraycpp2c = "cfficonvert_wrappedtype_cpp2c_array"
        klass.type = klass.unscopedName
        self.getTypeInfo(klass)

        # Create a subclass of the C++ type if we have any virtual or
        # protected methods
        klass.pureVirtualAbstract = (
            not klass.abstract and
            len([i for i in klass if getattr(i, 'isPureVirtual', False)]) > 0)
        klass.hasSubClass = (
            not klass.abstract and
            len([i for i in klass if isinstance(i, extractors.MethodDef) and
                                     (i.protection == 'protected' or
                                      i.isVirtual)]) > 0)
        klass.cppClassName = (klass.cName if not klass.hasSubClass
                                          else SUBCLASS_PREFIX + klass.cName)

        if klass.abstract:
            klass.items = [i for i in klass if not getattr(i, 'isCtor', False)]

        # Typenames of nested classes used in this class don't have to use the
        # type's full name. This messes up the type lookup, so replace short
        # names with the full name. This can be pretty simple because we are
        # only supporting nesting of a maximum depth of 1.
        for innerclass in klass.innerclasses:
            innerclass.klass = klass

            innerclass.pyName = innerclass.pyName or innerclass.name
            innerclass.unscopedPyName = klass.pyName + '.' + innerclass.pyName
            innerclass.unscopedName = klass.name + '::' + innerclass.name

            replace = r'\1' + innerclass.unscopedName
            pattern = re.compile(r'( |^)%s' % innerclass.name)
            for item in klass:
                if isinstance(getattr(item, 'type', None), str):
                    item.type = pattern.sub(replace, item.type)
            self.initClass(innerclass)

        ctor = klass.findItem(klass.name)
        klass.hasDefaultCtor = (ctor is None or
                                any(len(m.items) == 0 for m in ctor.all()))


    def initClassItems(self, klass):
        ctor = klass.findItem(klass.name)
        if ctor is None and not klass.abstract:
            assert klass.hasDefaultCtor
            # If the class doesn't have a ctor specified, we need to add a
            # default ctor
            ctor = extractors.MethodDef(
                name=klass.name,
                argsString='()',
                isCtor=True
            )
            klass.addItem(ctor)
        # Add a copy constructor
        # TODO: do we need to check for an existing copy ctor?
        if not klass.abstract:
            ctor.overloads.append(extractors.MethodDef(
                name=klass.name,
                argsString='(const %s & other)' % klass.unscopedName,
                items=[extractors.ParamDef(
                        type='const %s &' % klass.unscopedName,
                        name='other')
                    ],
                isCtor=True
            ))

        if klass.hasSubClass:
            # While we init the class's items, we'll build a list of the
            # virtual and protected methods' declarations to place in the
            # subclass's body
            klass.virtualMethods = []
            klass.protectedMethods = []

        # Move all Py*Def items into a seperate list
        pydefTypes = (extractors.PyMethodDef, extractors.PyPropertyDef,
                      extractors.PyCodeDef)
        klass.pyItems = categorize(klass.items, pydefTypes)[0]

        klass.keepReferenceIndex = -2

        dispatchItems(self.dispatchClassItemInit, klass.items, parent=klass)

        if klass.hasSubClass:
            klass.vtableDef = 'void(*%s_vtable[%d])();' % (klass.cName,
                                                     len(klass.virtualMethods))

        for ic in klass.innerclasses:
            self.initClassItems(ic)

    def initMappedType(self, mType):
        mType.pyName = mType.name
        mType.unscopedName = mType.name
        mType.unscopedPyName = mType.name

        templateClass = "cfficonvert_mappedtype<%s, %s>::" % (mType.name,
                                                              mType.cType)

        mType.arrayc2cpp = templateClass + 'c2cpp_array'
        mType.arraycpp2c = templateClass + 'cpp2c_array'
        mType.py2cFunc = '%s_py2c' % mType.name
        mType.cpp2cFunc = templateClass + 'cpp2c'
        mType.c2pyFunc = '%s_c2py' % mType.name

        # Because c2cpp must be called from Python, we need two versions of it
        mType.c2cppPyFunc = '%s_c2cpp' % mType.name
        mType.c2cppFunc = templateClass + 'c2cpp'

    def initFunction(self, func, overload=''):
        assert not func.ignored

        self.getTypeInfo(func)
        self.createArgsStrings(func, overload != '' or func.hasOverloads())

        returnVars = []
        if func.type.name != 'void':
            returnVars.append('return_tmp')
        returnVars.extend([p.type.c2py(p.name + OUT_PARAM_SUFFIX) for p in func
                           if p.type.out or p.type.inOut])
        func.returnCount = len(returnVars)
        if func.returnCount > 0:
            func.returnVars = '(' + ', '.join(returnVars) + ')'
        else:
            func.returnVars = None

        func.pyName = func.pyName or func.name
        func.cName = FUNC_PREFIX + func.name + overload
        func.retStmt = 'return ' if func.type.name != 'void' else ''
        func.briefDoc = func.briefDoc if func.briefDoc is not None else ''

        for i, f in enumerate(func.overloads):
            self.initFunction(f, '_%d' % i)

    def initMethod(self, method, parent, overload=''):
        assert not method.ignored

        if method.isCtor:
            method.type = parent.unscopedName + '*'
            method.pyName = '__init__'
        if method.isDtor:
            # We need a special case for the dtor since '~' isn't allowed in an
            # function name
            method.pyName = '__del__'
            method.cName = METHOD_PREFIX + parent.cName + '_88_delete'
        elif method.name in magicMethods:
            method.pyName = magicMethods[method.name]
            method.cName = ('%s%s_88_operator%s%s' %
                            (METHOD_PREFIX, parent.cName,
                             method.pyName.strip('_'), overload))
        else:
            method.cName = '%s%s_88_%s%s' % (METHOD_PREFIX, parent.cName,
                                             method.name, overload)

        method.pyName = method.pyName or method.name
        method.retStmt = 'return ' if method.name != 'void' else ''
        method.briefDoc = method.briefDoc if method.briefDoc is not None else ''

        if method.isVirtual:
            method.virtualIndex = len(parent.virtualMethods)
            parent.virtualMethods.append(method)
        if method.protection == 'protected':
            parent.protectedMethods.append(method)

        for param in method.items:
            if param.keepReference:
                param.keepReference = parent.keepReferenceIndex
                parent.keepReferenceIndex -= 1

        self.getTypeInfo(method)
        self.createArgsStrings(method, overload != '' or method.hasOverloads(),
                               parent)

        returnVars = []
        if method.type.name != 'void':
            returnVars.append('return_tmp')
        returnVars.extend([p.type.c2py(p.name + OUT_PARAM_SUFFIX) for p in method
                           if p.type.out or p.type.inOut])
        method.returnCount = len(returnVars)
        if method.returnCount > 0:
            method.returnVars = '(' + ', '.join(returnVars) + ')'
        else:
            method.returnVars = None

        for i, m in enumerate(method.overloads):
            if isinstance(m, extractors.CppMethodDef):
                self.initCppMethod(m, parent, '_%d' % i)
            else:
                self.initMethod(m, parent, '_%d' % i)

    def initCppMethod(self, method, parent=None, overload=''):
        assert not method.ignored

        method.pyName = method.name
        method.cppCode = (method.body, 'function')

        # CppMethodDefs have no ParamDefs, just an arg string. Build the list
        # of ParamDefs to make the CppMethodDef look more like a FunctionDef
        method.items = self.disassembleArgsString(method.argsString)

        if parent is None:
            self.initFunction(method, overload)
        else:
            self.initMethod(method, parent, overload)

    def initDefine(self, define):
        assert not define.ignored
        define.cName = DEFINE_PREFIX + define.name

    def initEnum(self, enum, parent=None):
        assert not enum.ignored
        for val in enum.items:
            assert not val.ignored
        enum.cPrefix = ENUM_PREFIX + ('' if parent is None
                                           else (parent.cName + '_88_'))
        enum.cppPrefix = '' if parent is None else (parent.unscopedName + '::')

    def initGlobalVar(self, var):
        assert not var.ignored
        self.getTypeInfo(var)
        var.pyName = var.pyName or var.name
        var.cName = GLOBAL_VAR_PREFIX + var.name

    def initMemberVar(self, var, parent):
        assert not var.ignored
        self.getTypeInfo(var)
        var.pyName = var.pyName or var.name
        prefix = MEMBER_VAR_PREFIX + parent.cName
        var.getName = prefix + "_88_get_" + var.name
        var.setName = prefix + "_88_set_" + var.name
        # TODO: Implement protected member vars. Currently, they are all
        #       suppressed by the tweakers, so we can wait until that changes
        #       to add them.


    #------------------------------------------------------------------------#

    def printClassCDefs(self, klass, pyfile):
        if klass.hasSubClass and len(klass.virtualMethods) > 0:
            pyfile.write(nci("""\
            {0.vtableDef}
            void {0.cName}_set_flag(void *, int);
            void {0.cName}_set_flags(void *, char*);""".format(klass)))
        dispatchItems(self.dispatchClassItemCDefs, klass.items, pyfile)

        for ic in klass.innerclasses:
            self.printClassCDefs(ic, pyfile)

    def printFunctionCDef(self, func, pyfile):
        print >> pyfile, "%s %s%s;" % (func.type.cdefType, func.cName,
                                       func.cdefArgs)
        for f in func.overloads:
            self.printFunctionCDef(f, pyfile)

    def printMethodCDef(self, method, pyfile):
        if not method.isPureVirtual:
            self.printFunctionCDef(method, pyfile)

    def printCppMethodCDef(self, method, pyfile):
        self.printFunctionCDef(method, pyfile)

    def printDefineCDef(self, define, pyfile):
        print >> pyfile, "extern const int %s;" % define.cName

    def printEnumCDef(self, enum, pyfile):
        for val in enum:
            print >> pyfile, "extern const int %s;" % (enum.cPrefix + val.name)

    def printGlobalVarCDef(self, var, pyfile):
        print >> pyfile, "extern %s %s;" % (var.type.cdefType, var.cName)

    def printMemberVarCDef(self, var, pyfile):
        print >> pyfile, "%s %s(void*);" % (var.type.cdefType, var.getName)
        print >> pyfile, "void %s(void*, %s);" % (var.setName,
                                                  var.type.cdefType)

    def printMappedTypeCDef(self, mType, pyfile):
        print >> pyfile, "void * %s(%s);" % (mType.c2cppPyFunc, mType.cType)

    #------------------------------------------------------------------------#

    def printClassCppBody(self, klass, cppfile):
        for ic in klass.innerclasses:
            self.printClassCppBody(ic, cppfile)

        if not klass.hasSubClass:
            return

        cppfile.write(nci("""\
        class {0} : public {1}
        {{
        public:""".format(klass.cppClassName, klass.unscopedName)))

        #ctors = [m for m in klass if getattr(m, 'isCtor', False)][0].all()
        ctors = klass.findItem(klass.name).all()
        # Signatures all Ctors
        for ctor in ctors:
            cppfile.write(nci("""\
            {0.cppClassName}{1.cppArgs}
                : {0.unscopedName}{1.cppCallArgs}
            {{}};""".format(klass, ctor), 4))


        # Signatures for re-implemented virtual methods
        if len(klass.virtualMethods) > 0:
            cppfile.write(nci("""\
            signed char vflags[%d];
            //Reimplement every virtual method"""
            % len(klass.virtualMethods), 4))
        for vmeth in klass.virtualMethods:
            if vmeth.isDtor:
                print >> cppfile, "    virtual ~%s();" % klass.cppClassName
                continue
            print >> cppfile, ("    virtual {0.type.name} {0.name}{0.cppArgs};"
                               .format(vmeth))

        # Signatures for protected methods
        if len(klass.protectedMethods) > 0:
            print >> cppfile, '    //Reimplement every protected method'
        for pmeth in klass.protectedMethods:
            if pmeth.isCtor:
                continue
            print >> cppfile, ("    {0.type.name} unprotected_{0.name}"
                               "{0.cppArgs};").format(pmeth)

        print >> cppfile, "};"

        if len(klass.virtualMethods) > 0:
            cppfile.write(nci("""\
            extern "C" {0}

            extern "C" void {1}_set_flag({2} * self, int i)
            {{
                self->vflags[i] = 1;
            }}

            extern "C" void {1}_set_flags({2} * self, char * flags)
            {{
                memcpy(self->vflags, flags, sizeof(self->vflags));
            }}""".format(klass.vtableDef, klass.cName, klass.cppClassName)))

    def printClass(self, klass, pyfile, cppfile, parent=None, indent=0):
        baseClassDefs = [self.findItem(b) for b in klass.bases]

        if klass.abstract:
            pyfile.write(nci("@wrapper_lib.abstract_class", indent))
        elif any([b.abstract for b in baseClassDefs]):
            pyfile.write(nci("@wrapper_lib.concrete_subclass", indent))
        elif klass.pureVirtualAbstract:
            pyfile.write(nci("@wrapper_lib.purevirtual_abstract_class", indent))

        pyBases = ', '.join([b.pyName for b in baseClassDefs])
        if pyBases == '':
            pyBases = 'wrapper_lib.CppWrapper'
        pyfile.write(nci("""\
        class %s(%s):
            __metaclass__ = wrapper_lib.WrapperType"""
        % (klass.pyName, pyBases), indent))

        if klass.hasSubClass and len(klass.virtualMethods) > 0:
            pyfile.write(nci("""\
            _vtable = clib.{0}_vtable

            def _set_vflag(self, i):
                clib.{0}_set_flag(wrapper_lib.get_ptr(self), i)

            def _set_vflags(self, flags):
                clib.{0}_set_flags(wrapper_lib.get_ptr(self), flags)
            """.format(klass.cName), indent + 4))

        if hasattr(klass, 'convertPy2Cpp'):
            pyfile.write(nci("""\
            class _pyobject_mapping_(object):
                __metaclass__ = wrapper_lib.MMTypeCheckMeta
            """, indent + 4))

            pyfile.write(nci("""\
            @staticmethod
            def __instancecheck__(obj):""", indent + 8))
            pyfile.write(nci(klass.instancecheck, indent + 12))

            noneTest = '' if klass.allowNone else 'py_obj is None or '
            pyfile.write(nci("""\
            @staticmethod
            def convert(py_obj):
                if %sissubclass(type(py_obj), %s):
                    return py_obj
            """ % (noneTest, klass.unscopedPyName), indent + 8))
            pyfile.write(nci(klass.convertPy2Cpp, indent + 12))

        dispatchItems(self.dispatchClassItemPrint, klass.items, pyfile, cppfile,
                 indent=indent + 4, parent=klass)

        for ic in klass.innerclasses:
            self.printClass(ic, pyfile, cppfile, indent=indent + 4,
                            parent=klass)

    def printExternCWrapper(self, func, call, cppfile):
        cppfile.write(nci("""\
        extern "C" {0.type.cType} {0.cName}{0.cArgs}
        {{""".format(func)))
        for param in func.items:
            convertCode = param.type.c2cppPrecall(param.name)
            if convertCode is not None:
                cppfile.write(nci(convertCode, 4))

        if func.type.name == 'void':
            cppfile.write(nci(call + ';', 4))
        else:
            cppfile.write(nci("%s return_tmp = %s;" % (func.type.name, call), 4))

        for param in func.items:
            cleanupCode = param.type.c2cppPostcall(param.name)
            if cleanupCode is not None:
                cppfile.write(nci(cleanupCode, 4))

        if func.type.name != 'void':
            cppfile.write(nci("return %s;" % func.type.cpp2c("return_tmp"), 4))
        print >> cppfile, "}"

    def printFunction(self, func, pyfile, cppfile, isOverload=False):
        # Figure out the name of the C++ function that we want to call from our
        # extern C wrapper. By default it is the C++ function we're wrapping,
        # but if we have custom code, it needs to be the name of the wrapper
        # where we're putting the custom code.
        callName = func.name
        if func.cppCode is not None:
            callName, wrapperBody = self.createCppCodeWrapper(func)
            cppfile.write(wrapperBody)

        self.printExternCWrapper(func, callName + func.cCallArgs, cppfile)

        if func.hasOverloads():
            isOverload = True
            pyfile.write(nci("""\
            @wrapper_lib.StaticMultimethod
            def %s():""" % func.pyName))
            self.printDocString(func, pyfile)
            print >> pyfile, ' ' * 4 + 'pass'

        call = "clib." + func.cName + func.pyCallArgs
        if isOverload:
            print >> pyfile, "@%s.overload%s" % (func.pyName,
                                                 func.overloadArgs)
        print >> pyfile, "def %s%s:" % (func.pyName, func.pyArgs)
        if not isOverload:
            self.printDocString(func, pyfile)

        if not isOverload:
            # Do type checking on functions that aren't overloaed inside the
            # funciton body
            pyfile.write(nci("wrapper_lib.check_args_types" +
                             func.overloadArgs, 4))

        for p in func.items:
            convertCode = p.type.py2cPrecall(p.name)
            if convertCode is not None:
                pyfile.write(nci(convertCode, 4))

        if func.returnVars is None:
            print >> pyfile, "    clib.%s%s" % (func.cName, func.pyCallArgs)
            self.printOwnershipChanges(func, pyfile)
        else:
            print >> pyfile, "    return_tmp = " + func.type.c2py("clib.%s%s"
                             % (func.cName, func.pyCallArgs))
            self.printOwnershipChanges(func, pyfile)
            print >> pyfile, "    return " + func.returnVars

        for f in func.overloads:
            self.printFunction(f, pyfile, cppfile, True)


    def printMethod(self, method, pyfile, cppfile, indent, parent,
                    isOverload=False):
        # Write C++ implementation
        if method.isVirtual:
            funcPtrName = '%s_%s_FUNCPTR' % (parent.cName, method.virtualIndex)
            cbCall = ('(({0}){2.cName}_vtable[{1.virtualIndex}]){1.cbCallArgs}'
                      .format(funcPtrName, method, parent))

            if not method.isDtor:
                sig = ("{0.type.name} {1.cppClassName}::{0.name}{0.cppArgs}"
                        .format(method, parent))
            else:
                sig = "{0.cppClassName}::~{0.cppClassName}()".format(parent)

            cppfile.write(nci("""\
            extern "C" typedef {0.type.cReturnType} (*{2}){0.cCbArgs};
            {3}
            {{
            """
            .format(method, parent, funcPtrName, sig)))
            if not method.isPureVirtual:
                # Pure virtual methods don't have an original implementation to
                # call, so only checking the flag if this isn't pure virtual
                cppfile.write(nci("""\
                if(this->vflags[{0.virtualIndex}])
                {{
                """
                .format(method), 4))

            for param in method.items:
                convertCode = param.type.virtualPreCallback(param.name)
                if convertCode is not None:
                    cppfile.write(nci(convertCode, 8))

            if method.type.name == 'void':
                cppfile.write(nci(cbCall + ';', 8))
            else:
                cppfile.write(nci("""\
                    {0.type.cReturnType} py_return = {1};
                """.format(method, cbCall), 8))

            for param in method.items:
                convertCode = param.type.virtualPostCallback(param.name)
                if convertCode is not None:
                    cppfile.write(nci(convertCode, 8))

            if method.type.name != 'void':
                isMappedType = isinstance(method.type, MappedTypeInfo)
                isWrappedType = isinstance(method.type, WrappedTypeInfo)
                isBasicType = isinstance(method.type, BasicTypeInfo)

                if isBasicType or method.type.isPtr and (isMappedType or
                   isWrappedType):
                    cppfile.write(nci("return py_return;", 8))
                elif (isWrappedType or isMappedType) and method.type.isRef:
                    cppfile.write(nci("return *py_return;", 8))
                else:
                    assert isMappedType
                    assert not method.type.isPtr and not method.type.isRef
                    cppfile.write(nci("""\
                    {0} return_instance = *py_return;
                    delete py_return;
                    return return_instance;
                    """.format(method.type.name), 8))

            if not method.isPureVirtual:
                cppfile.write(nci("""\
                    }}
                    else
                        {0.retStmt}{1.unscopedName}::{0.name}{0.cppCallArgs};"""
                .format(method, parent), 4))
            print >> cppfile, '}'

        if method.cppCode is not None:
            callName, wrapperBody = self.createCppCodeWrapper(method)
            print >> cppfile, wrapperBody
            call = callName + method.wrapperCallArgs
        elif method.protection == 'protected' and not method.isCtor:
            # We only need to do the special handling of a protected method if
            # it has no custom code.
            callName = PROTECTED_PREFIX + method.name
            cppfile.write(nci("""\
            {0.type.name} {1.cppClassName}::{2}{0.cppArgs}
            {{
                {0.retStmt}{1.unscopedName}::{0.name}{0.cppCallArgs};
            }}""".format(method, parent, callName)))

            call = "self->" + callName + method.cCallArgs
        elif method.isStatic:
            call = ("{1.unscopedName}::{0.name}{0.cCallArgs}"
                    .format(method, parent))
        elif method.isCtor:
            call = "new " + parent.cppClassName +  method.cCallArgs
        else:
            # Just in case, we'll always specify the original implementation,
            # for both regular and virtual methods
            call = ("self->{1.unscopedName}::{0.name}{0.cCallArgs}"
                    .format(method, parent))

        if method.isDtor:
            call = 'delete self'
        if not method.isPureVirtual:
            # Pure virtual methods cannot have an extern "C" wrapper as they
            # cannot be called directly.
            self.printExternCWrapper(method, call, cppfile)

        # Write Python implementation
        if method.isVirtual:
            call = '{0}.{1.pyName}{1.vtdCallArgs}'.format(
                    parent.type.c2py('self'), method)
            pyfile.write(nci("""\
            @wrapper_lib.VirtualDispatcher({0.virtualIndex})
            @ffi.callback('{0.type.cdefReturnType}(*){0.cdefCbArgs}')
            def _virtual__{0.virtualIndex}{0.vtdArgs}:
                return_tmp = {1}
            """.format(method, call), indent))

            for i, param in enumerate([p for p in method if p.type.out or
                                                            p.type.inOut]):
                i += 1 if method.type.name != 'void' else 0
                returnVar = 'return_tmp'
                if method.returnCount > 1:
                    returnVar += '[%d]' % i

                convertCode = param.type.py2cPostcall(returnVar, param.name)
                if convertCode is not None:
                    pyfile.write(nci(convertCode, indent + 4))

            if method.type.name != 'void':
                varName = 'return_tmp'
                if method.returnCount > 1:
                    varName += '[0]'

                convertCode = method.type.py2cPostcall(varName, 'return_tmp')
                if convertCode is not None:
                    pyfile.write(nci(convertCode, indent + 4))

                if method.factory:
                    pyfile.write(nci(
                        'wrapper_lib.give_ownership(wrapper_lib.obj_from_ptr('
                        'return_tmp, %s), None, True)' %
                        method.type.typedef.unscopedPyName, indent + 4))

                pyfile.write(nci('return return_tmp', indent + 4))

            pyfile.write(nci("@wrapper_lib.VirtualMethod(%d)" %
                                     method.virtualIndex,
                                     indent))

        if method.hasOverloads():
            isOverload = True
            mmType = '' if not method.isStatic else 'Static'
            pyfile.write(nci("""\
            @wrapper_lib.{1}Multimethod
            def {0.pyName}():""".format(method, mmType), indent))
            self.printDocString(method, pyfile, indent)
            print >> pyfile, ' ' * (indent + 4) + 'pass'

        if isOverload:
            pyfile.write(nci("""\
            @{0.pyName}.overload{0.overloadArgs}
            """.format(method, parent), indent))

        if method.isStatic and not isOverload:
            # @staticmethod isn't needed if this is a multimethod because the
            # StaticMutlimethod decorator takes care of it
            pyfile.write(nci("@staticmethod", indent))

        pyfile.write(nci("def {0.pyName}{0.pyArgs}:".format(method), indent))
        if not isOverload:
            self.printDocString(method, pyfile, indent)

        if not isOverload:
            # Do type checking on non-multi method's inside the method's body
            pyfile.write(nci("wrapper_lib.check_args_types" +
                             method.overloadArgs, indent + 4))

        if not method.isPureVirtual:
            for p in method.items:
                convertCode = p.type.py2cPrecall(p.name)
                if convertCode is not None:
                    pyfile.write(nci(convertCode, indent + 4))

            call = 'clib.{0.cName}{0.pyCallArgs}'.format(method)
            if method.isCtor:
                pyfile.write(nci("""\
                cpp_obj = %s
                wrapper_lib.CppWrapper.__init__(self, cpp_obj)
                """ % call, indent + 4))
                self.printOwnershipChanges(method, pyfile, indent, parent)
            elif method.returnVars is None:
                pyfile.write(nci(call, indent + 4))
                self.printOwnershipChanges(method, pyfile, indent, parent)
            else:
                pyfile.write(nci("return_tmp = " + method.type.c2py(call),
                                indent + 4))
                self.printOwnershipChanges(method, pyfile, indent, parent)
                pyfile.write(nci("return " +  method.returnVars, indent + 4))
        else:
            pyfile.write(nci(
                "raise NotImplementedError('%s.%s() is abstract and must be "
                "overridden')" % (parent.pyName, method.pyName), indent + 4))

        for m in method.overloads:
            self.printMethod(m, pyfile, cppfile, indent, parent, True)

    def printOwnershipChanges(self, func, pyfile, indent=0, parent=None):
        owner = ''
        if func.factory:
            owner = ', return_tmp'
        elif isinstance(func, extractors.MethodDef) and not func.isStatic:
            owner = ", self"

        for param in [p for p in func if isinstance(p.type, WrappedTypeInfo)]:
            if param.keepReference is not False:
                key = ''
                if isinstance(func, extractors.MethodDef) and not func.isStatic:
                    key = ", %d" % param.keepReference
                pyfile.write(nci("wrapper_lib.keep_reference(" + param.name +
                                 key + owner + ')', indent + 4))

            if param.transfer and not param.array:
                pyfile.write(nci("wrapper_lib.give_ownership(%s%s)" %
                                 (param.name, owner), indent + 4))
            if param.transferBack:
                pyfile.write(nci("wrapper_lib.take_ownership(%s)" %
                                 param.name, indent + 4))
            if param.transferThis:
                obj = "return_tmp" if func.factory else "self"
                pyfile.write(nci("""\
                if {0} is None:
                    wrapper_lib.take_ownership({1})
                else:
                    wrapper_lib.give_ownership({1}, {0})
                """.format(param.name, obj), indent + 4))

        if func.transfer:
            assert not getattr(func, 'isStatic', True)
            if not func.isCtor:
                pyfile.write(nci(
                    "wrapper_lib.give_ownership(return_tmp, self)",
                    indent + 4))
            else:
                pyfile.write(nci("wrapper_lib.give_ownership(self, "
                                 "external_ref=True)", indent + 4))
        elif func.transferBack:
            pyfile.write(nci("wrapper_lib.take_ownership(return_tmp)",
                             indent + 4))

        elif func.transferThis:
            pyfile.write(nci("wrapper_lib.give_ownership(self)", indent + 4))
        elif func.factory:
            pyfile.write(nci("wrapper_lib.take_ownership(return_tmp)", indent + 4))

    def printCppMethod(self, func, pyfile, cppfile, indent=0, parent=None):
        if parent is None:
            self.printFunction(func, pyfile, cppfile)
        else:
            self.printMethod(func, pyfile, cppfile, indent, parent)

    def printProperty(self, property, pyfile, cppfile, indent, parent):
        pyfile.write(nci("{0.name} = property({0.getter}, {0.setter})"
                         .format(property), indent))


    def printDefine(self, define, pyfile, cppfile):
        print >> pyfile, "%s = clib.%s" % (define.pyName, define.cName)
        print >> cppfile, ("""extern "C" const int %s = %s;""" %
                              (define.cName, define.name))

    def printEnum(self, enum, pyfile, cppfile, indent=0, parent=None):
        for val in enum.items:
            cName = enum.cPrefix + val.name
            cppName = enum.cppPrefix + val.name
            print >> cppfile, ('extern "C" const int %s = %s;' % (cName, cppName))
            print >> pyfile, (' ' * indent + '%s = clib.%s' % (val.name, cName))

    def printGlobalVar(self, var, pyfile, cppfile):
        print >> cppfile, ('extern "C" {0.type.cType} {0.cName} = {1};'.
                            format(var, var.type.cpp2c(var.name)))
        print >> pyfile, var.pyName + ' = ' + var.type.c2py('clib.' + var.cName)

    def printMemberVar(self, var, pyfile, cppfile, indent, parent):
        varName = "self->" + var.name

        convertCode = var.type.c2cppPrecall('value')
        if convertCode is None:
            convertCode = ''

        cleanupCode = var.type.c2cppPostcall('value')
        if cleanupCode is None:
            cleanupCode = ''

        cppfile.write(nci("""\
        extern "C" {0.type.cType} {0.getName}({1.unscopedName} * self)
        {{
            return {2};
        }}

        extern "C" void {0.setName}({1.unscopedName} * self, {0.type.cType} value)
        {{
            {3}
            self->{0.name} = {5};
            {4}
        }}
        """.format(var, parent, var.type.cpp2c(varName), convertCode,
                   cleanupCode, var.type.c2cppParam('value'))))

        py2cCode = var.type.py2cPrecall('value', inplace=True)
        if py2cCode is None:
            py2cCode = 'value'

        c2pyCode = var.type.c2py('clib.%s(wrapper_lib.get_ptr(self))' %
                                 (var.getName))
        pyfile.write(nci("""\
        {0.pyName} = property(
            lambda self: {1},
            lambda self, value: clib.{0.setName}(wrapper_lib.get_ptr(self), {2}))
        """.format(var, c2pyCode, py2cCode), indent))

    def printMappedType(self, mType, pyfile, cppfile, indent):
        cppfile.write(nci("""\
        template<>
        {0.cType} cfficonvert_mappedtype<{0.name}, {0.cType}>::
            cpp2c({0.name} *cpp_obj)
        {{
{1}
        }}

        template<>
        {0.name} * cfficonvert_mappedtype<{0.name}, {0.cType}>::
            c2cpp({0.cType} cdata)
        {{
{2}
        }}

        extern "C" {0.name} * {0.c2cppPyFunc}({0.cType} cdata)
        {{
            return {0.c2cppFunc}(cdata);
        }}
        """.format(mType, nci(mType.cpp2c, 12), nci(mType.c2cpp, 12))))

        checkCode = nci(mType.instancecheck or 'pass', 16)
        c2pyCode = nci(mType.c2py or 'pass', 16)
        py2cCode = nci(mType.py2c or 'pass', 16)
        pyfile.write(nci("""\
        class {0.name}(wrapper_lib.MappedBase):
            @classmethod
            def __instancecheck__(cls, obj):
{1}
            @classmethod
            def c2py(cls, cdata):
{2}
            @classmethod
            def py2c(cls, py_obj):
                if py_obj is None:
                    return ffi.NULL
{3}
        """.format(mType, checkCode, c2pyCode, py2cCode)))

    #------------------------------------------------------------------------#

    def printClassFinalization(self, klass, pyfile):
        print >> pyfile, ('wrapper_lib.eval_class_attrs(%s)' %
                          klass.unscopedPyName)
        '''
        if klass.hasDefaultCtor:
            pyfile.write(nci("""\
            {0}Seq = wrapper_lib.create_array_type({0})"""
            .format(klass.unscopedPyName, klass.cName)))
        '''
        for ic in klass.innerclasses:
            self.printClassFinalization(ic, pyfile)

    def printFunctionFinalization(self, func, pyfile):
        if func.hasOverloads():
            print >> pyfile, "%s.finalize()" % func.pyName
        elif any(p.default != '' for p in func.items):
            print >> pyfile, ("wrapper_lib.eval_func_defaults(%s)" %
                               func.pyName)

    def printCppMethodFinalization(self, method, pyfile, parent=None):
        if parent is None:
            self.printFunctionFinalization(method, pyfile)

    #------------------------------------------------------------------------#

    def printClassPyDefs(self, klass, pyfile):
        dispatchItems(self.dispatchPrintClassPyDefs, klass.pyItems, pyfile,
                      0, klass)

        for ic in klass.innerclasses:
            self.printClassPyDefs(ic, pyfile)

    def printPyClass(self, klass, pyfile, indent):
        if len(klass.bases) == 0:
            klass.bases.append('object')
        bases = ', '.join(klass.bases)
        pyfile.write(nci("class %s(%s):" % (klass.name, bases), indent))
        self.printDocString(klass, pyfile, indent)

        dispatchItems(self.dispatchPrintPyClassItems, klass.items, pyfile,
                      indent + 4)


    def printPyFunction(self, func, pyfile, indent):
        pyfile.write(nci('def {0.name}{0.argsString}:'.format(func), indent))
        self.printDocString(func, indent)
        pyfile.write(nci(func.body, indent + 4))

    def printPyCode(self, code, pyfile, indent):
        pyfile.write(nci(code.code, indent))

    def printPyProperty(self, property, pyfile, indent, parent=None):
        if parent is not None:
            isinstance(parent, extractors.ClassDef)
            pyfile.write(nci(
            "{1.unscopedPyName}.{0.name} = "
            "property({1.unscopedPyName}.{0.getter}, "
            "{1.unscopedPyName}.{0.setter})".format(property, parent)))
        else:
            self.printProperty(property, pyfile, None, indent, parent)

    def printPyMethod(self, method, pyfile, indent, parent):
        escapedPyName = method.klass.unscopedPyName.replace('.', '__')
        methName = "_{1}_{0.name}".format(method, escapedPyName)
        assignName = methName
        if method.isStatic:
            assignName = "staticmethod(" + assignName + ")"
        if method.deprecated:
            # XXX: this is wxPython specific, maybe it should be more general?
            assignName = "wx.deprecated(" + assignName + ")"

        print >> pyfile, 'def %s%s:' % (methName, method.argsString)
        self.printDocString(method, pyfile)
        pyfile.write(nci(method.body, 4))
        pyfile.write(nci("""\
        {0.klass.unscopedPyName}.{0.name} = {1}
        del {2}""".format(method, assignName, methName)))

    #------------------------------------------------------------------------#

    def getTypeInfo(self, item):
        if isinstance(item.type, (str, types.NoneType)):
            item.type = TypeInfo.new(
                item.type, self.findItem,
                pyInt=getattr(item, 'pyInt', False),
                array=getattr(item, 'array', False),
                arraySize=getattr(item, 'arraySize', False),
                out=getattr(item, 'out', False),
                inOut=getattr(item, 'inOut', False),
                noCopy=getattr(item, 'noCopy', False),
                transfer=getattr(item, 'transfer', False),
                factory=getattr(item, 'factory', False))

    def createArgsStrings(self, func, isOverload, parent=None):
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
        func.cCbArgs = []
        func.cdefCbArgs = []
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

        if parent is not None and not func.isStatic:
            func.pyArgs.append('self')
            if not func.isCtor:
                func.pyCallArgs.append('wrapper_lib.get_ptr(self)')
                func.cArgs.append('%s *self' % parent.cppClassName)
                func.cdefArgs.append('void *self')
                func.cCbArgs.append('%s *self' % parent.cppClassName)
                func.cdefCbArgs.append('void *self')
                func.cbCallArgs.append('this')
                func.vtdArgs.append('self')

        for i, param in enumerate(func.items):
            if param.arraySize:
                # Rename the ArraySize parameter so we don't have to look for
                # in the param list elsewhere
                param.name = ARRAY_SIZE_PARAM

            self.getTypeInfo(param)

            cArg = "%s %s" % (param.type.cType, param.name)
            #cdefArg = "%s %s" % (param.type.cdefType, param.name)
            cdefArg = param.type.cdefType
            cCbArg = param.type.cCbType
            cdefCbArg = param.type.cdefCbType
            cCallArg = param.type.c2cppParam(param.name)
            cbCallArg = param.type.cpp2c(param.name)

            cppArg = "%s %s" % (param.type.name, param.name)
            cppCallArg = "%s" % param.name

            pyArg = param.name
            if param.default != '':
                pyArg += '=' + defValueMap.get(param.default,
                               'wrapper_lib.LD("%s")' % param.default)

            pyCallArg = param.type.py2cParam(param.name)
            vtdArg = param.name
            vtdCallArg = param.type.c2py(param.name)

            if not isOverload:
                overloadArg = '%s, %s, "%s"' % (param.type.overloadType,
                                                param.name, param.name)
            elif param.type.typedef is None:
                overloadArg = param.name + '=' + param.type.overloadType
            else:
                overloadArg = param.name + "='" + param.type.overloadType + "'"

            func.cArgs.append(cArg)
            func.cdefArgs.append(cdefArg)
            func.cCbArgs.append(cCbArg)
            func.cdefCbArgs.append(cdefCbArg)
            func.cCallArgs.append(cCallArg)
            func.cbCallArgs.append(cbCallArg)
            func.cppArgs.append(cppArg)
            func.cppCallArgs.append(cppCallArg)
            #func.pyArgs.append(pyArg)
            func.pyCallArgs.append(pyCallArg)
            func.vtdArgs.append(vtdArg)
            #func.vtdCallArgs.append(vtdCallArg)
            #func.overloadArgs.append(overloadArg)

            if not param.type.out and not param.type.arraySize:
                func.pyArgs.append(pyArg)
                func.overloadArgs.append(overloadArg)
                func.vtdCallArgs.append(vtdCallArg)

        if parent is not None and not func.isStatic and not func.isCtor:
            # We're generating a wrapper function that needs a `self` pointer
            # in its args string if this function has custom C++ code or is
            # protected and not static
            func.wrapperArgs = ([parent.cppClassName + " *self"] +
                                func.cppArgs)
            func.wrapperCallArgs = ['self'] + func.cppCallArgs
        else:
            func.wrapperArgs = func.cppArgs
            func.wrapperCallArgs = func.cppCallArgs

        func.cArgs = '(' + ', '.join(func.cArgs) + ')'
        func.cdefArgs = '(' + ', '.join(func.cdefArgs) + ')'
        func.cCbArgs = '(' + ', '.join(func.cCbArgs) + ')'
        func.cdefCbArgs = '(' + ', '.join(func.cdefCbArgs) + ')'
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

    def printDocString(self, item, pyfile, indent=0):
        if item.briefDoc == '' or item.briefDoc is None:
            return

        quote = ' ' * (indent + 4) + '"""'
        print >> pyfile, quote
        pyfile.write(nci(item.briefDoc, indent + 4))
        print >> pyfile, quote

    def disassembleArgsString(self, argsString):
        """
        CppMethodDefs are always specified with an empty parameter list. So we
        can treat them like regular FunctionDefs where ever possible, we'll use
        this method to disassemble their args string into a list of ParamDefs.
        Based loosely on the extractors.FunctionDef.makePyArgsString
        """
        # XXX This really doesn't need to be a method. Maybe make it a global
        #     function later?
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
            param.type, param.name = arg.rsplit(' ', 1)
            params.append(param)

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
        wrapperBody = nci("""\
        {0.type.name} {1}{0.wrapperArgs}
        {{
        {2}
        }}""".format(func, wrapperName, nci(func.cppCode[0], 4)))

        return (wrapperName, wrapperBody)

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
