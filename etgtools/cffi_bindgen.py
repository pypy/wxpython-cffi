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
    'char*': 'str',
    'char *': 'str',
    'signed char': 'int',
    'unsigned char': 'int',
    'bool': 'bool',
    'void': None,
}

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

class TypeInfo(object):
    _cache = {}
    def __init__(self, typeName, findItem, pyInt=False):
        if typeName == '' or typeName is None:
            typeName = 'void'
        self.name = typeName
        self.isRef = False
        self.isPtr = False
        self.isConst = 'const ' in typeName
        self.pyInt = pyInt

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
            self.cType = typedef.unscopedName
        else:
            self.cType = typeName
        if self.isRef or self.isPtr or isinstance(typedef, extractors.ClassDef):
            self.cType += ' *'

        if self.isConst:
            self.cType = 'const ' + self.cType

        # Type for the cdef that will be called by cffi. Same rules as cType,
        # but must also treat all pointers to wrapped classes as `void *`
        if isinstance(typedef, extractors.EnumDef) or typeName == 'bool':
            self.cdefType = 'int'
        elif isinstance(typedef, extractors.ClassDef):
            self.cdefType = 'void'
        elif self.pyInt:
            assert typeName in ('char', 'signed char', 'unsigned char')
            self.cdefType = 'signed char'
        elif typeName == 'unsigned char':
            # For compatibility, we want to treat all char types like strings,
            # which is different from cffi's default behavior for (un)signed
            # chars.
            self.cdefType = typeName.replace('unsigned char', 'char')
        elif typeName == 'signed char':
            self.cdefType = typeName.replace('signed char', 'char')
        else:
            self.cdefType = typeName
        if self.isRef or self.isPtr or isinstance(self.typedef,
                                                  extractors.ClassDef):
            self.cdefType += ' *'

        # We need to dereference the pointer if our c type is a pointer but the
        # the type original type is not
        self.deref = self.cType[-1] == '*' and self.isPtr

        if self.isCBasic:
            if 'char' not in self.cType or self.pyInt:
                # All of the c basics that not strings are numbers
                self.overloadType = 'numbers.Number'
            else:
                self.overloadType = '(str, unicode)'
        else:
            self.overloadType = self.typedef.unscopedPyName

    @classmethod
    def new(cls, typeName, findItem, **kwargs):
        key = (typeName, frozenset(kwargs.items()))
        if key not in cls._cache:
            typeInfo = TypeInfo(typeName, findItem, **kwargs)
            cls._cache[typeName] = typeInfo
            return typeInfo
        return cls._cache[key]

    @classmethod
    def clearCache(cls):
        cls._cache = {}

    def cpp2c(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            # Always pass wrapped classes as pointers. If this is by value or
            # a const reference, it needs to be copy constructored onto the
            # heap, with Python taking ownership of the new object.
            if self.isPtr:
                return varName
            elif self.isRef and not self.isConst:
                return '&' + varName
            else:
                return "new %s(%s)" % (self.typedef.cppClassName, varName)
        elif self.isCBasic:
            # C basic types don't need anything special
            return varName
        raise Exception()

    def c2py(self, varName):
        if isinstance(self.typedef, extractors.ClassDef):
            return 'wrapper_lib.obj_from_ptr(%s, %s)' % (varName,
                                                         self.typedef.unscopedPyName)
        elif self.isCBasic:
            if 'char *' in self.name or 'char*' in self.name:
                return "ffi.string(%s)" % varName
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
            extractors.FunctionDef      : self.printFunction,
            extractors.CppMethodDef     : self.printCppMethod,
            extractors.DefineDef        : self.printDefine,
            extractors.GlobalVarDef     : self.printGlobalVar,
            extractors.EnumDef          : self.printEnum,
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
                                extractors.ClassDef)
        self.pyItems, self.classes, self.globalItems = categories

        self.pyItems.sort(key=lambda item: item.order if item.order is not None
                                                      else sys.maxint)

        for klass in self.classes:
            self.initClass(klass)
        self.sortClasses()

        for klass in self.classes:
            self.initClassItems(klass)
        dispatchItems(self.dispatchInit, self.globalItems)


    # TODO: some of the C++ code needs to written to a seperate header file so
    #       that other modules can access this modules declarations
    def writeFiles(self, pyfile, cppfile, verify_args=''):
        # Write the C++ preamble
        print >> cppfile, "#include <cstring>"
        for attr in ('headerCode', 'cppCode', 'initializerCode',
                     'preInitializerCode', 'postInitializerCode'):
            for line in getattr(self.module, attr):
                print >> cppfile, line

        # Write Python preamble
        print >> pyfile, nci("""\
        import cffi
        import numbers
        import wrapper_lib""")
        for module in self.module.imports:
            print >> pyfile, "import %s" % module

        # Write cdefs
        print >> pyfile, nci("""\
        ffi = cffi.FFI()
        cdefs = ('''""")
        for klass in self.classes:
            self.printClassCDefs(klass, pyfile)
        dispatchItems(self.dispatchCDefs, self.globalItems, pyfile)
        print >> pyfile, nci("""\
        ''')
        ffi.cdef(cdefs)
        clib = ffi.verify(cdefs, %s)
        del cdefs""" % verify_args)

        # Print classes' C++ bodies, before any method bodies are printed
        for klass in self.classes:
            self.printClassCppBody(klass, cppfile)

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

        klass.type = klass.unscopedName
        self.getTypeInfo(klass)

        # Create a subclass of the C++ type if we have any virtual or
        # protected methods
        klass.hasSubClass = len([i for i in klass
                                   if isinstance(i, extractors.MethodDef) and
                                      (i.protection == 'protected' or
                                       i.isVirtual)]) > 0
        klass.cppClassName = (klass.cName if not klass.hasSubClass
                                          else SUBCLASS_PREFIX + klass.cName)

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


    def initClassItems(self, klass):
        ctor = klass.findItem(klass.name)
        if ctor is None:
            # If the class doesn't have a ctor specified, we need to add a
            # default ctor
            ctor = extractors.MethodDef(
                name=klass.name,
                argsString='()',
                isCtor=True
            )
            klass.addItem(ctor)

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

        dispatchItems(self.dispatchClassItemInit, klass.items, parent=klass)

        if klass.hasSubClass:
            klass.vtableDef = 'void(*%s_vtable[%d])();' % (klass.cName,
                                                     len(klass.virtualMethods))

        for ic in klass.innerclasses:
            self.initClassItems(ic)

    def initFunction(self, func, overload=''):
        assert not func.ignored

        self.getTypeInfo(func)
        self.createArgsStrings(func)

        func.pyName = func.pyName or func.name
        func.cName = FUNC_PREFIX + func.name + overload
        func.retStmt = 'return ' if func.type.name != 'void' else ''
        func.briefDoc = func.briefDoc if func.briefDoc is not None else ''

        for i, f in enumerate(func.overloads):
            self.initFunction(f, '_%d' % i)

    def initMethod(self, method, parent, overload=''):
        assert not method.ignored

        if method.isCtor:
            method.type = parent.unscopedName
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

        self.getTypeInfo(method)
        self.createArgsStrings(method, parent)

        for i, m in enumerate(method.overloads):
            self.initMethod(m, parent, '_%d' % i)

    def initCppMethod(self, method, parent=None):
        assert not method.ignored

        method.pyName = method.name
        method.cppCode = (method.body, 'function')

        # CppMethodDefs have no ParamDefs, just an arg string. Build the list
        # of ParamDefs to make the CppMethodDef look more like a FunctionDef
        method.items = self.disassembleArgsString(method.argsString)

        if parent is None:
            self.initFunction(method)
        else:
            self.initMethod(method, parent)

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

        # Add a copy ctor that takes an instance of the original class
        cppfile.write(nci("""\
        {0.cppClassName}(const {0.name} &other)
            : {0.unscopedName}(other)
        {{}};""".format(klass), 4))


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
        pyBases = ', '.join([self.findItem(b).pyName for b in klass.bases])
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

        dispatchItems(self.dispatchClassItemPrint, klass.items, pyfile, cppfile,
                 indent=indent + 4, parent=klass)

        for ic in klass.innerclasses:
            self.printClass(ic, pyfile, cppfile, indent=indent + 4,
                            parent=klass)


    def printFunction(self, func, pyfile, cppfile, isOverload=False):
        # Figure out the name of the C++ function that we want to call from our
        # extern C wrapper. By default it is the C++ function we're wrapping,
        # but if we have custom code, it needs to be the name of the wrapper
        # where we're putting the custom code.
        callName = func.name
        if func.cppCode is not None:
            callName, wrapperBody = self.createCppCodeWrapper(func)
            cppfile.write(wrapperBody)

        cppfile.write(nci("""\
        extern "C" {0.type.cType} {0.cName}{0.cArgs}
        {{
            {0.retStmt}{1}{0.cCallArgs};
        }}""".format(func, callName)))

        if func.hasOverloads():
            isOverload = True
            pyfile.write(nci("""\
            @wrapper_lib.StaticMultimethod
            def %s():""" % func.pyName))
            self.printDocString(func, pyfile)
            print >> pyfile, ' ' * 4 + 'pass'

        if isOverload:
            print >> pyfile, "@%s.overload%s" % (func.pyName,
                                                 func.overloadArgs)
        print >> pyfile, "def %s%s:" % (func.pyName, func.pyArgs)
        if not isOverload:
            self.printDocString(func, pyfile)

        if func.type.name == 'void':
            print >> pyfile, "    clib.%s%s" % (func.cName, func.pyCallArgs)
        else:
            print >> pyfile, "    ret_value = " + func.type.c2py("clib.%s%s"
                               % (func.cName, func.pyCallArgs))
            # TODO: handle annotations
            print >> pyfile, "    return ret_value"

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
            extern "C" typedef {0.type.cType} (*{2}){0.cArgs};
            {4}
            {{
                if(this->vflags[{0.virtualIndex}])
                    {0.retStmt}{3};
                else
                    {0.retStmt}{1.unscopedName}::{0.name}{0.cppCallArgs};
            }}"""
            .format(method, parent, funcPtrName, method.type.c2cpp(cbCall),
                    sig)))

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
            # method.type.cpp2c will add the ClassName() part, so use the args
            call = method.cCallArgs[1:-1]
        else:
            # Just in case, we'll always specify the original implementation,
            # for both regular and virtual methods
            call = ("self->{1.unscopedName}::{0.name}{0.cCallArgs}"
                    .format(method, parent))

        operation = 'return ' if method.type.name != 'void' else ''
        if method.isDtor:
            body = 'delete self;'
        else:
            body = operation + method.type.cpp2c(call) + ';'
        cppfile.write(nci("""\
        extern "C" %s %s%s
        {
            %s
        }""" % (method.type.cdefType, method.cName, method.cArgs, body)))

        # Write Python implementation
        if method.isVirtual:
            call = '{0}.{1.pyName}{1.vtdCallArgs}'.format(
                    parent.type.c2py('self'), method)
            pyfile.write(nci("""\
            @wrapper_lib.VirtualDispatcher({0.virtualIndex})
            @ffi.callback('{0.type.cdefType}(*){0.cdefArgs}')
            def _virtual__{0.virtualIndex}{0.vtdArgs}:
                return {1}
            """.format(method, method.type.py2c(call)), indent))

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

        call = 'clib.{0.cName}{0.pyCallArgs}'.format(method)
        if method.isCtor:
            pyfile.write(nci("def __init__%s:" % (method.pyArgs), indent))
            if not isOverload:
                self.printDocString(method, pyfile, indent)
            pyfile.write(nci("""\
            cpp_obj = %s
            wrapper_lib.CppWrapper.__init__(self, cpp_obj)
            """ % call, indent + 4))
        else:
            pyfile.write(nci("def {0.pyName}{0.pyArgs}:".format(method), indent))
            if not isOverload:
                self.printDocString(method, pyfile, indent)
            pyfile.write(nci("return %s" % method.type.c2py(call), indent + 4))

        for m in method.overloads:
            self.printMethod(m, pyfile, cppfile, indent, parent, True)


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
        cppfile.write(nci("""\
        extern "C" {0.type.cType} {0.getName}({1.unscopedName} * self)
        {{
            return self->{0.name};
        }}

        extern "C" void {0.setName}({1.unscopedName} * self, {0.type.cType} value)
        {{
            self->{0.name} = value;
        }}
        """.format(var, parent)))

        pyfile.write(nci("""\
        {0.pyName} = property(
            lambda self: clib.{0.getName}(wrapper_lib.get_ptr(self)),
            lambda self, value: clib.{0.setName}(wrapper_lib.get_ptr(self), {1}))
        """.format(var, var.type.py2c('value')), indent))

    #------------------------------------------------------------------------#

    def printClassFinalization(self, klass, pyfile):
        print >> pyfile, ('wrapper_lib.eval_class_attrs(%s)' %
                          klass.unscopedPyName)
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
            item.type = TypeInfo.new(item.type, self.findItem,
                                     pyInt=getattr(item, 'pyInt', False))

    def createArgsStrings(self, func, parent=None):
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

        if parent is not None and not func.isStatic:
            func.pyArgs.append('self')
            if not func.isCtor:
                func.pyCallArgs.append('wrapper_lib.get_ptr(self)')
                func.cArgs.append('%s *self' % parent.cppClassName)
                func.cdefArgs.append('void *self')
                func.cbCallArgs.append('this')
                func.vtdArgs.append('self')


        for param in func.items:
            self.getTypeInfo(param)

            cArg = "%s %s" % (param.type.cType, param.name)
            cdefArg = "%s %s" % (param.type.cdefType, param.name)
            cCallArg = param.type.c2cpp(param.name)
            cbCallArg = param.type.cpp2c(param.name)

            cppArg = "%s %s" % (param.type.name, param.name)
            cppCallArg = "%s" % param.name

            pyArg = param.name
            if param.default != '':
                pyArg += '=' + defValueMap.get(param.default,
                               'wrapper_lib.LD("%s")' % param.default)

            pyCallArg = param.type.py2c(param.name)
            vtdArg = param.name
            vtdCallArg = param.type.c2py(param.name)

            if param.type.typedef is None:
                overloadArg = param.name + '=' + param.type.overloadType
            else:
                overloadArg = param.name + "='" + param.type.overloadType + "'"

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


        if parent is not None and not func.isStatic:
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
