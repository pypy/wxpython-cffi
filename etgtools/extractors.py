#---------------------------------------------------------------------------
# Name:        etgtools/extractors.py
# Author:      Robin Dunn
#
# Created:     3-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

"""
Functions and classes that can parse the Doxygen XML files and extract the
wxWidgets API info which we need from them.
"""

import sys
import os
import re
import pprint
import xml.etree.ElementTree as et

from .tweaker_tools import FixWxPrefix, magicMethods, \
                           guessTypeInt, guessTypeFloat, guessTypeStr, \
                           textfile_open, getGenerator
from sphinxtools.utilities import FindDescendants

#---------------------------------------------------------------------------
# These classes simply hold various bits of information about the classes,
# methods, functions and other items in the C/C++ API being wrapped.
#
# NOTE: Currently very little is being done with the docstrings. They can
# either be reprocessed later by the document generator or we can do more
# tinkering with them here.  It just depends on decisions not yet made...
#---------------------------------------------------------------------------

class BaseDef(object):
    """
    The base class for all element types and provides the common attributes
    and functions that they all share.
    """
    nameTag = 'name'
    def __init__(self, element=None):
        self.name = ''          # name of the item
        self.pyName = ''        # rename to this name
        self.ignored = False    # skip this item
        self.briefDoc = ''      # either a string or a single para Element
        self.detailedDoc = []   # collection of para Elements

        # The items list is used by some subclasses to collect items that are
        # part of that item, like methods of a ClassDef, etc.
        self.items = []

        if element is not None:
            self.extract(element)

    def __iter__(self):
        return iter(self.items)


    def extract(self, element):
        # Pull info from the ElementTree element that is pertinent to this
        # class. Should be overridden in derived classes to get what each one
        # needs in addition to the base.
        self.name = element.find(self.nameTag).text
        if '::' in self.name:
            loc = self.name.rfind('::')
            self.name = self.name[loc+2:]
        bd = element.find('briefdescription')
        if len(bd):
            self.briefDoc = bd[0] # Should be just one <para> element
        self.detailedDoc = list(element.find('detaileddescription'))


    def ignore(self, val=True):
        self.ignored = val
        return self


    def find(self, name):
        """
        Locate and return an item within this item that has a matching name.
        The name string can use a dotted notation to continue the search
        recursively.  Raises ExtractorError if not found.
        """
        try:
            head, tail = name.split('.', 1)
        except ValueError:
            head, tail = name, None
        for item in self._findItems():
            if item.name == head or item.pyName == head:  # TODO: exclude ignored items?
                if not tail:
                    return item
                else:
                    return item.find(tail)
            if isinstance(item, EnumDef):
                try:
                    return item.find(head)
                except ExtractorError:
                    pass

        else: # got though all items with no match
            raise ExtractorError("Unable to find item named '%s' within %s named '%s'" %
                                 (head, self.__class__.__name__, self.name))

    def findItem(self, name):
        """
        Just like find() but does not raise an exception if the item is not found.
        """
        try:
            item = self.find(name)
            return item
        except ExtractorError:
            return None


    def addItem(self, item):
        self.items.append(item)
        return item

    def insertItem(self, index, item):
        self.items.insert(index, item)
        return item

    def insertItemAfter(self, after, item):
        try:
            idx = self.items.index(after)
            self.items.insert(idx+1, item)
        except ValueError:
            self.items.append(item)
        return item

    def insertItemBefore(self, before, item):
        try:
            idx = self.items.index(before)
            self.items.insert(idx, item)
        except ValueError:
            self.items.insert(0, item)
        return item


    def allItems(self):
        """
        Recursively create a sequence for traversing all items in the
        collection. A generator would be nice but just prebuilding a list will
        be good enough.
        """
        items = [self]
        for item in self.items:
            items.extend(item.allItems())
            if hasattr(item, 'overloads'):
                for o in item.overloads:
                    items.extend(o.allItems())
            if hasattr(item, 'innerclasses'):
                for o in item.innerclasses:
                    items.extend(o.allItems())

        return items


    def findAll(self, name):
        """
        Search recursivly for items that have the given name.
        """
        matches = list()
        for item in self.allItems():
            if item.name == name or item.pyName == name:
                matches.append(item)
        return matches


    def _findItems(self):
        # If there are more items to be searched than what is in self.items, a
        # subclass can override this to give a different list.
        return self.items



#---------------------------------------------------------------------------

class VariableDef(BaseDef):
    """
    Represents a basic variable declaration.
    """
    def __init__(self, element=None, **kw):
        super(VariableDef, self).__init__()
        self.type = None
        self.definition = ''
        self.argsString = ''
        self.pyInt = False
        self.__dict__.update(**kw)
        if element is not None:
            self.extract(element)

    def extract(self, element):
        super(VariableDef, self).extract(element)
        self.type = flattenNode(element.find('type'))
        self.definition = element.find('definition').text
        self.argsString = element.find('argsstring').text



#---------------------------------------------------------------------------
# These need the same attributes as VariableDef, but we use separate classes
# so we can identify what kind of element it came from originally.

class GlobalVarDef(VariableDef):
    pass


class TypedefDef(VariableDef):
    def __init__(self, element=None, **kw):
        super(TypedefDef, self).__init__()
        self.noTypeName = False
        self.docAsClass = False
        self.bases = []
        self.platformDependent = False
        self.__dict__.update(**kw)
        if element is not None:
            self.extract(element)

#---------------------------------------------------------------------------

class MemberVarDef(VariableDef):
    """
    Represents a variable declaration in a class.
    """
    def __init__(self, element=None, **kw):
        super(MemberVarDef, self).__init__()
        self.isStatic = False
        self.protection = 'public'
        self.__dict__.update(kw)
        if element is not None:
            self.extract(element)

    def extract(self, element):
        super(MemberVarDef, self).extract(element)
        self.isStatic = element.get('static') == 'yes'
        self.protection = element.get('prot')
        assert self.protection in ['public', 'protected']
        # TODO: Should protected items be ignored by default or should we
        #       leave that up to the tweaker code or the generators?
        if self.protection == 'protected':
            self.ignore()


#---------------------------------------------------------------------------

_globalIsCore = None

class FunctionDef(BaseDef, FixWxPrefix):
    """
    Information about a standalone function.
    """
    def __init__(self, element=None, **kw):
        super(FunctionDef, self).__init__()
        self.type = None
        self.definition = ''
        self.argsString = ''
        self.pyArgsString = ''
        self.isOverloaded = False
        self.overloads = []
        self.deprecated = False       # is the function deprecated
        self.factory = False          # a factory function that creates a new instance of the return value
        self.pyReleaseGIL = False     # release the Python GIL for this function call
        self.pyHoldGIL = False        # hold the Python GIL for this function call
        self.noCopy = False           # don't make a copy of the return value, just wrap the original
        self.pyInt = False            # treat char types as integers
        self.transfer = False         # transfer ownership of return value to C++?
        self.transferBack = False     # transfer ownership of return value from C++ to Python?
        self.transferThis = False     # ownership of 'this' pointer transfered to C++
        self.cppCode = None           # Use this code instead of the default wrapper
        self.noArgParser = False      # set the NoargParser annotation
        self.__dict__.update(kw)
        if element is not None:
            self.extract(element)
        elif not hasattr(self, 'isCore'):
            self.isCore = _globalIsCore


    def extract(self, element):
        super(FunctionDef, self).extract(element)
        self.type = flattenNode(element.find('type'))
        self.definition = element.find('definition').text
        self.argsString = element.find('argsstring').text
        for node in element.findall('param'):
            p = ParamDef(node)
            self.items.append(p)
            # TODO: Look at self.detailedDoc and pull out any matching
            # parameter description items and assign that value as the
            # briefDoc for this ParamDef object.


    def releaseGIL(self, release=True):
        self.pyReleaseGIL = release

    def holdGIL(self, hold=True):
        self.pyHoldGIL = hold


    def setCppCode_sip(self, code):
        """
        Use the given C++ code instead of that automatically generated by the
        back-end. This is similar to adding a new C++ method, except it uses
        info we've already received from the source XML such as the argument
        types and names, docstring, etc.

        The code generated for this verison will expect the given code to use
        SIP specfic variable names, etc. For example::

            sipRes = sipCpp->Foo();
        """
        self.cppCode = (code, 'sip')


    def setCppCode(self, code):
        """
        Use the given C++ code instead of that automatically generated by the
        back-end. This is similar to adding a new C++ method, except it uses
        info we've already received from the source XML such as the argument
        types and names, docstring, etc.

        The code generated for this version will put the given code in a
        wrapper function that will enable it to be more independent, not SIP
        specific, and also more natural. For example::

            return self->Foo();
        """
        self.cppCode = (code, 'function')


    def setOriginalTypesCppCode(self, code):
        """
        Use the given C++ code instead of that automatically generated by the
        back-end. This is similar to adding a new C++ method, except it uses
        info we've already received from the source XML such as the argument
        types and names, docstring, etc.

        The code generated for this version will put the given code in a
        wrapper function that will enable it to be more independent, not SIP
        specific, and also more natural. For example::

            return self->Foo();

        The types of the parameters passed to the given code will be the
        original types instead of the sip-ized types setCppCode uses.
        """
        self.cppCode = (code, 'original_types')


    def checkForOverload(self, methods):
        for m in methods:
            if isinstance(m, FunctionDef) and m.name == self.name:
                m.overloads.append(self)
                m.isOverloaded = self.isOverloaded = True
                return True
        return False


    def all(self):
        return [self] + self.overloads


    def findOverload(self, matchText, isConst=None, printSig=False):
        """
        Search for an overloaded method that has matchText in its C++ argsString.
        """
        for o in self.all():
            if printSig:
                print("%s%s" % (o.name, o.argsString))
            if matchText in o.argsString and not o.ignored:
                if isConst is None:
                    return o
                else:
                    if o.isConst == isConst:
                        return o
        return None


    def hasOverloads(self):
        """
        Returns True if there are any overloads that are not ignored.
        """
        return bool([x for x in self.overloads if not x.ignored])


    def renameOverload(self, matchText, newName, **kw):
        """
        Rename the overload with matching matchText in the argsString to
        newName. The overload is moved out of this function's overload list
        and directly into the parent module or class so it can appear to be a
        separate function.
        """
        if hasattr(self, 'module'):
            parent = self.module
        else:
            parent = self.klass
        item = self.findOverload(matchText)
        item.pyName = newName
        item.__dict__.update(kw)

        if item is self and not self.hasOverloads():
            # We're done, there actually is only one instance of this method
            pass
        elif item is self:
            # Make the first overload take the place of this node in the
            # parent, and then insert this item into the parent's list again
            overloads = self.overloads
            overloads.sort(key=lambda o: o.ignored)
            self.overloads = []
            first = overloads[0]
            first.overloads = overloads[1:]
            idx = parent.items.index(self)
            parent.items[idx] = first
            parent.insertItemAfter(first, self)

        else:
            # Just remove from the overloads list and insert it into the parent.
            self.overloads.remove(item)
            parent.insertItemAfter(self, item)
        return item


    def ignore(self,  val=True):
        # If the item being ignored has overloads then try to reorder the
        # items so the primary item is not an ignored one.
        super(FunctionDef, self).ignore(val)
        if val and self.overloads:
            all = [self] + self.overloads
            all.sort(key=lambda item: item.ignored)
            first = all[0]
            if not first.ignored:
                if hasattr(self, 'module'):
                    parent = self.module
                else:
                    parent = self.klass
                self.overloads = []
                first.overloads = all[1:]
                idx = parent.items.index(self)
                parent.items[idx] = first
        return self


    def _findItems(self):
        items = list(self.items)
        for o in self.overloads:
            items.extend(o.items)
        return items


    def makePyArgsString(self):
        """
        Create a pythonized version of the argsString in function and method
        items that can be used as part of the docstring.

        TODO: Maybe (optionally) use this syntax to document arg types?
              http://www.python.org/dev/peps/pep-3107/
        """
        def _cleanName(name):
            for txt in ['const', '*', '&', ' ']:
                name = name.replace(txt, '')
            name = name.replace('::', '.')
            name = self.fixWxPrefix(name, True)
            return name

        params = list()
        returns = list()
        if self.type and self.type != 'void':
            returns.append(_cleanName(self.type))

        defValueMap = { 'true':  'True',
                        'false': 'False',
                        'NULL':  'None',
                        'wxString()': '""',
                        'wxArrayString()' : '[]',
                        'wxArrayInt()' : '[]',
                        }
        if isinstance(self, CppMethodDef):
            # rip appart the argsString instead of using the (empty) list of parameters
            lastP = self.argsString.rfind(')')
            args = self.argsString[:lastP].strip('()').split(',')
            for arg in args:
                if not arg:
                    continue
                # is there a default value?
                default = ''
                if '=' in arg:
                    default = arg.split('=')[1].strip()
                    arg = arg.split('=')[0].strip()
                    if default in defValueMap:
                        default = defValueMap.get(default)
                    else:
                        default = self.fixWxPrefix(default, True)
                # now grab just the last word, it should be the variable name
                arg = arg.split()[-1]
                if default:
                    arg += '=' + default
                params.append(arg)
        else:
            for param in self.items:
                assert isinstance(param, ParamDef)
                if param.ignored:
                    continue
                if param.arraySize:
                    continue
                s = param.pyName or param.name
                if param.out:
                    returns.append(s)
                else:
                    if param.inOut:
                        returns.append(s)
                    if param.default:
                        default = param.default
                        if default in defValueMap:
                            default = defValueMap.get(default)

                        s += '=' + '|'.join([_cleanName(x) for x in default.split('|')])
                    params.append(s)

        self.pyArgsString = '(' + ', '.join(params) + ')'
        if len(returns) == 1:
            self.pyArgsString += ' -> ' + returns[0]
        if len(returns) > 1:
            self.pyArgsString += ' -> (' + ', '.join(returns) + ')'


    def collectPySignatures(self):
        """
        Collect the pyArgsStrings for self and any overloads, and create a
        list of function signatures for the docstrings.
        """
        sigs = list()
        for f in [self] + self.overloads:
            assert isinstance(f, FunctionDef)
            if f.ignored:
                continue
            if not f.pyArgsString:
                f.makePyArgsString()

            sig = f.pyName or self.fixWxPrefix(f.name)
            if sig in magicMethods:
                sig = magicMethods[sig]
            sig += f.pyArgsString
            sigs.append(sig)
        return sigs

#---------------------------------------------------------------------------

class MethodDef(FunctionDef):
    """
    Represents a class method, ctor or dtor declaration.
    """
    def __init__(self, element=None, className=None, **kw):
        super(MethodDef, self).__init__()
        self.className = className
        self.isVirtual = False
        self.isPureVirtual = False
        self.isStatic = False
        self.isConst = False
        self.isCtor = False
        self.isDtor = False
        self.protection = 'public'
        self.defaultCtor = False      # use this ctor as the default one
        self.noDerivedCtor = False    # don't generate a ctor in the derived class for this ctor
        self.cppSignature = None
        self.virtualCatcherCode = None
        self.__dict__.update(kw)
        if element is not None:
            self.extract(element)
        elif not hasattr(self, 'isCore'):
            self.isCore = _globalIsCore


    def extract(self, element):
        super(MethodDef, self).extract(element)
        self.isStatic = element.get('static') == 'yes'
        self.isVirtual = element.get('virt') in ['virtual', 'pure-virtual']
        self.isPureVirtual = element.get('virt') == 'pure-virtual'
        self.isConst = element.get('const') == 'yes'
        self.isCtor = self.name == self.className
        self.isDtor = self.name == '~' + self.className
        self.protection = element.get('prot')
        assert self.protection in ['public', 'protected']
        # TODO: Should protected items be ignored by default or should we
        #       leave that up to the tweaker code or the generators?
        if self.protection == 'protected':
            self.ignore()




#---------------------------------------------------------------------------

class ParamDef(BaseDef):
    """
    A parameter of a function or method.
    """
    def __init__(self, element=None, **kw):
        super(ParamDef, self).__init__()
        self.type = ''                # data type
        self.default = ''             # default value
        self.out = False              # is it an output arg?
        self.inOut = False            # is it both input and output?
        self.pyInt = False            # treat char types as integers
        self.array = False            # the param is to be treated as an array
        self.arraySize = False        # the param is the size of the array
        self.transfer = False         # transfer ownership of arg to C++?
        self.transferBack = False     # transfer ownership of arg from C++ to Python?
        self.transferThis = False     # ownership of 'this' pointer transfered to this arg
        self.keepReference = False    # an extra reference to the arg is held
        self.__dict__.update(kw)
        if element is not None:
            self.extract(element)

    def extract(self, element):
        try:
            self.type = flattenNode(element.find('type'))
            # we've got varags
            if self.type == '...':
                self.name = ''
            else:
                if element.find('declname') is not None:
                    self.name = element.find('declname').text
                elif element.find('defname') is not None:
                    self.name = element.find('defname').text
            if element.find('defval') is not None:
                self.default = flattenNode(element.find('defval'))
        except:
            print("error when parsing element:")
            et.dump(element)
            raise
#---------------------------------------------------------------------------

class ClassDef(BaseDef):
    """
    The information about a class that is needed to generate wrappers for it.
    """
    nameTag = 'compoundname'
    def __init__(self, element=None, kind='class', **kw):
        super(ClassDef, self).__init__()
        self.kind = kind
        self.protection = 'public'
        self.templateParams = []    # class is a template
        self.bases = []             # base class names
        self.subClasses = []        # sub classes
        self.nodeBases = []         # for the inheritance diagram
        self.enum_file = ''         # To link sphinx output classes to enums
        self.includes = []          # .h file for this class
        self.abstract = False       # is it an abstract base class?
        self.deprecated = False     # mark all methods as deprecated
        self.external = False       # class is in another module
        self.noDefCtor = False      # do not generate a default constructor
        self.singlton = False       # class is a singleton so don't call the dtor until the interpreter exits
        self.allowAutoProperties = True
        self.headerCode = []
        self.cppCode = []
        self.convertToPyObject = None
        self.convertFromPyObject = None
        self.allowNone = False      # Allow the convertFrom code to handle None too.
        self.instanceCode = None    # Code to be used to create new instances of this class
        self.innerclasses = []
        self.isInner = False

        self.pyCode_cffi = None     # Extra code to include in the class body
        self.convertFromPyObject_cffi = None
        self.instanceCheck_cffi = None
        self.detectSubclassCode_cffi = None

        # Stuff that needs to be generated after the class instead of within
        # it. Some back-end generators need to put stuff inside the class, and
        # others need to do it outside the class definition. The generators
        # can move things here for later processing when they encounter those
        # items.
        self.generateAfterClass = []

        self.__dict__.update(kw)
        if element is not None:
            self.extract(element)


    def findHierarchy(self, element, all_classes, specials, read):

        from etgtools import XMLSRC

        if not read:
            nodename = fullname = self.name
            specials = [nodename]
        else:
            nodename = fullname = element.text

        baselist = []

        if read:
            refid = element.get('refid')
            if refid is None:
                return all_classes, specials

            fname = os.path.join(XMLSRC, refid+'.xml')
            root = et.parse(fname).getroot()
            compounds = FindDescendants(root, 'basecompoundref')
        else:
            compounds = element.findall('basecompoundref')

        for c in compounds:
            baselist.append(c.text)

        all_classes[nodename] = (nodename, fullname, baselist)

        for c in compounds:
            all_classes, specials = self.findHierarchy(c, all_classes, specials, True)

        return all_classes, specials


    def extract(self, element):
        super(ClassDef, self).extract(element)

        self.nodeBases = self.findHierarchy(element, {}, [], False)

        for node in element.findall('basecompoundref'):
            self.bases.append(node.text)
        for node in element.findall('derivedcompoundref'):
            self.subClasses.append(node.text)
        for node in element.findall('includes'):
            self.includes.append(node.text)
        for node in element.findall('templateparamlist/param'):
            txt = node.find('type').text
            txt = txt.replace('class ', '')
            self.templateParams.append(txt)

        for node in element.findall('innerclass'):
            if node.get('prot') == 'private':
                continue
            from etgtools import XMLSRC
            ref = node.get('refid')
            fname = os.path.join(XMLSRC, ref+'.xml')
            root = et.parse(fname).getroot()
            innerclass = root[0]
            kind = innerclass.get('kind')
            assert kind in ['class', 'struct']
            item = ClassDef(innerclass, kind)
            item.protection = node.get('prot')
            item.isInner = True
            self.innerclasses.append(item)


        # TODO: Is it possible for there to be memberdef's w/o a sectiondef?
        for node in element.findall('sectiondef/memberdef'):
            # skip any private items
            if node.get('prot') == 'private':
                continue
            kind = node.get('kind')
            if kind == 'function':
                m = MethodDef(node, self.name, klass=self)
                if not m.checkForOverload(self.items):
                    self.items.append(m)
            elif kind == 'variable':
                v = MemberVarDef(node)
                self.items.append(v)
            elif kind == 'enum':
                e = EnumDef(node, [self])
                self.items.append(e)
            elif kind == 'typedef':
                # callback function prototype, see wx/filedlg.h for an instance of this
                continue
            elif kind == 'friend':
                continue
            else:
                raise ExtractorError('Unknown memberdef kind: %s' % kind)


    def _findItems(self):
        return self.items + self.innerclasses


    def addHeaderCode(self, code):
        if isinstance(code, list):
            self.headerCode.extend(code)
        else:
            self.headerCode.append(code)

    def addCppCode(self, code):
        if isinstance(code, list):
            self.cppCode.extend(code)
        else:
            self.cppCode.append(code)


    def includeCppCode(self, filename):
        self.addCppCode(textfile_open(filename).read())


    def addAutoProperties(self):
        """
        Look at MethodDef and PyMethodDef items and generate properties if
        there are items that have Get/Set prefixes and have appropriate arg
        counts.
        """
        def countNonDefaultArgs(m):
            count = 0
            for p in m.items:
                if not p.default and not p.ignored:
                    count += 1
            return count

        def countPyArgs(item):
            count = 0
            args = item.argsString.replace('(', '').replace(')', '')
            for arg in args.split(','):
                if arg != 'self':
                    count += 1
            return count

        def countPyNonDefaultArgs(item):
            count = 0
            args = item.argsString.replace('(', '').replace(')', '')
            for arg in args.split(','):
                if arg != 'self' and '=' not in arg:
                    count += 1
            return count

        props = dict()
        for item in self.items:
            if isinstance(item, (MethodDef, PyMethodDef)) \
               and item.name not in ['Get', 'Set'] \
               and (item.name.startswith('Get') or item.name.startswith('Set')):
                prefix = item.name[:3]
                name = item.name[3:]
                prop = props.get(name, PropertyDef(name))
                if isinstance(item, PyMethodDef):
                    ok = False
                    argCount = countPyArgs(item)
                    nonDefaultArgCount = countPyNonDefaultArgs(item)
                    if prefix == 'Get' and argCount == 0:
                        ok = True
                        prop.getter = item.name
                        prop.usesPyMethod = True
                    elif prefix == 'Set'and \
                         (nonDefaultArgCount == 1 or (nonDefaultArgCount == 0 and argCount > 0)):
                        ok = True
                        prop.setter = item.name
                        prop.usesPyMethod = True

                else:
                    # look at all overloads
                    ok = False
                    for m in item.all():
                        # don't use ignored or static methods for propertiess
                        if m.ignored or m.isStatic:
                            continue
                        if prefix == 'Get':
                            prop.getter = m.name
                            # Getters must be able to be called with no args, ensure
                            # that item has exactly zero args without a default value
                            if countNonDefaultArgs(m) != 0:
                                continue
                            ok = True
                            break
                        elif prefix == 'Set':
                            prop.setter = m.name
                            # Setters must be able to be called with 1 arg, ensure
                            # that item has at least 1 arg and not more than 1 without
                            # a default value.
                            if len(m.items) == 0 or countNonDefaultArgs(m) > 1:
                                continue
                            ok = True
                            break
                if ok:
                    if hasattr(prop, 'usesPyMethod'):
                        prop = PyPropertyDef(prop.name, prop.getter, prop.setter)
                    props[name] = prop

        if props:
            self.addPublic()
        for name, prop in sorted(props.items()):
            # properties must have at least a getter
            if not prop.getter:
                continue
            starts_with_number = False
            try:
                int(name[0])
                starts_with_number = True
            except:
                pass

            # only create the prop if a method with that name does not exist, and it is a valid name
            if starts_with_number:
                print('WARNING: Invalid property name %s for class %s' % (name, self.name))
            elif self.findItem(name):
                print("WARNING: Method %s::%s already exists in C++ class API, can not create a property." % (self.name, name))
            else:
                self.items.append(prop)




    def addProperty(self, *args, **kw):
        """
        Add a property to a class, with a name, getter function and optionally
        a setter method.
        """
        # As a convenience allow the name, getter and (optionally) the setter
        # to be passed as a single string. Otherwise the args will be passed
        # as-is to PropertyDef
        if len(args) == 1:
            name = getter = setter = ''
            split = args[0].split()
            assert len(split) in [2 ,3]
            if len(split) == 2:
                name, getter = split
            else:
                name, getter, setter = split
            p = PropertyDef(name, getter, setter, **kw)
        else:
            p = PropertyDef(*args, **kw)
        self.items.append(p)
        return p



    def addPyProperty(self, *args, **kw):
        """
        Add a property to a class that can use PyMethods that have been
        monkey-patched into the class. (This property will also be
        jammed in to the class in like manner.)
        """
        # Read the nice comment in the function above.  Ditto.
        if len(args) == 1:
            name = getter = setter = ''
            split = args[0].split()
            assert len(split) in [2 ,3]
            if len(split) == 2:
                name, getter = split
            else:
                name, getter, setter = split
            p = PyPropertyDef(name, getter, setter, **kw)
        else:
            p = PyPropertyDef(*args, **kw)
        self.items.append(p)
        return p

    #------------------------------------------------------------------

    def _addMethod(self, md):
        md.klass = self
        if self.findItem(md.name):
            self.findItem(md.name).overloads.append(md)
        else:
            self.items.append(md)

    def addMethod(self, type, name, argsString, **kwargs):
        if isinstance(argsString, str) or isinstance(argsString, basestring):
            argsString = ArgsString(argsString)
        self._addMethod(MethodDef(type=type, name=name, items=argsString,
                                  **kwargs))

    def addCppMethod(self, type, name, argsString, body, doc=None, isConst=False,
                     cppSignature=None, **kw):
        """
        Add a new C++ method to a class. This method doesn't have to actually
        exist in the real C++ class. Instead it will be grafted on by the
        back-end wrapper generator such that it is visible in the class in the
        target language.
        """
        md = CppMethodDef(type, name, argsString, body, doc, isConst, klass=self,
                          cppSignature=cppSignature, **kw)
        self._addMethod(md)
        return md


    def addCppCtor(self, argsString, body, doc=None, noDerivedCtor=True,
                   useDerivedName=False, cppSignature=None, **kw):
        """
        Add a C++ method that is a constructor.
        """
        md = CppMethodDef('', self.name, argsString, body, doc=doc,
                          isCtor=True, klass=self, noDerivedCtor=noDerivedCtor,
                          useDerivedName=useDerivedName, cppSignature=cppSignature, **kw)
        self._addMethod(md)
        return md


    def addCppDtor(self, body, useDerivedName=False, **kw):
        """
        Add a C++ method that is a destructor.
        """
        md = CppMethodDef('', '~'+self.name, '()', body, isDtor=True, klass=self,
                          useDerivedName=useDerivedName, **kw)
        self._addMethod(md)
        return md


    def addCppMethod_sip(self, type, name, argsString, body, doc=None, **kw):
        """
        Just like the above but can do more things that are SIP specific in
        the code body, instead of using the general purpose implementation.
        """
        md = CppMethodDef_sip(type, name, argsString, body, doc, klass=self, **kw)
        self._addMethod(md)
        return md

    def addCppCtor_sip(self, argsString, body, doc=None, noDerivedCtor=True,
                       cppSignature=None, **kw):
        """
        Add a C++ method that is a constructor.
        """
        md = CppMethodDef_sip('', self.name, argsString, body, doc=doc,
                          isCtor=True, klass=self, noDerivedCtor=noDerivedCtor,
                          cppSignature=cppSignature, **kw)
        self._addMethod(md)
        return md

    #------------------------------------------------------------------


    def addPyMethod(self, name, argsString, body, doc=None, **kw):
        """
        Add a (monkey-patched) Python method to this class.
        """
        pm = PyMethodDef(self, name, argsString, body, doc, **kw)
        self.items.append(pm)
        return pm


    def addPyCode(self, code):
        """
        Add a snippet of Python code which is to be associated with this class.
        """
        pc = PyCodeDef(code, klass=self, protection = 'public')
        self.items.append(pc)
        return pc


    def addPublic(self, code=''):
        """
        Adds a 'public:' protection keyword to the class, optionally followed
        by some additional code.
        """
        text = 'public:'
        if code:
            text = text + '\n' + code
        self.addItem(WigCode(text))

    def addProtected(self, code=''):
        """
        Adds a 'protected:' protection keyword to the class, optionally followed
        by some additional code.
        """
        text = 'protected:'
        if code:
            text = text + '\n' + code
        self.addItem(WigCode(text))


    def addPrivate(self, code=''):
        """
        Adds a 'private:' protection keyword to the class, optionally followed
        by some additional code.
        """
        text = 'private:'
        if code:
            text = text + '\n' + code
        self.addItem(WigCode(text))


    def addCopyCtor(self, prot='protected'):
        # add declaration of a copy constructor to this class
        if getGenerator() == 'sip':
            wig = WigCode("""\
            {PROT}:
                {CLASS}(const {CLASS}&);""".format(CLASS=self.name, PROT=prot))
            self.addItem(wig)
        else:
            self.addMethod(
                "", self.name, "(const %s & other)" % self.name,
                isCtor=True, protection=prot
            )

    def addPrivateCopyCtor(self):
        self.addCopyCtor('private')

    def addPrivateAssignOp(self):
        # add declaration of an assignment opperator to this class
        if getGenerator() == 'sip':
            wig = WigCode("""\
            private:
                {CLASS}& operator=(const {CLASS}&);""".format(CLASS=self.name))
            self.addItem(wig)
        # TODO: Does the cffi backend actually care about private assign
        #       operators?
        #else:
        #    self.addMethod(
        #        self.name + '&', 'operator=', '(const %s & other)' % self.name,
        #        protection='private'
        #    )

    def addDtor(self, prot='protected'):
        # add declaration of a destructor to this class
        if getGenerator() == 'sip':
            wig = WigCode("""\
            {PROT}:
                ~{CLASS}();""".format(CLASS=self.name, PROT=prot))
            self.addItem(wig)
        else:
            self.addMethod("", '~' + self.name, "()", isDtor=True, protection=prot)

    def addDefaultCtor(self, prot='protected'):
        # add declaration of a default constructor to this class
        if getGenerator() == 'sip':
            wig = WigCode("""\
            {PROT}:
                {CLASS}();""".format(CLASS=self.name, PROT=prot))
            self.addItem(wig)
        else:
            self.addMethod("", self.name, "()", isCtor=True, protection=prot)


#---------------------------------------------------------------------------

class EnumDef(BaseDef):
    """
    A named or anonymous enumeration.
    """
    def __init__(self, element=None, inClass=[], **kw):
        super(EnumDef, self).__init__()
        self.inClass = inClass
        if element is not None:
            prot = element.get('prot')
            if prot is not None:
                self.protection = prot
                assert self.protection in ['public', 'protected']
                # TODO: Should protected items be ignored by default or should we
                #       leave that up to the tweaker code or the generators?
                if self.protection == 'protected':
                    self.ignore()
            self.extract(element)
        self.__dict__.update(kw)

    def extract(self, element):
        super(EnumDef, self).extract(element)
        for node in element.findall('enumvalue'):
            value = EnumValueDef(node)
            self.items.append(value)




class EnumValueDef(BaseDef):
    """
    An item in an enumeration.
    """
    def __init__(self, element=None, **kw):
        super(EnumValueDef, self).__init__()
        if element is not None:
            self.extract(element)
        self.__dict__.update(kw)


#---------------------------------------------------------------------------

class DefineDef(BaseDef):
    """
    Represents a #define with a name and a value.
    """
    def __init__(self, element=None, **kw):
        super(DefineDef, self).__init__()
        if element is not None:
            self.name = element.find('name').text
            self.value = flattenNode(element.find('initializer'))
        self.__dict__.update(kw)


#---------------------------------------------------------------------------

class PropertyDef(BaseDef):
    """
    Use the C++ methods of a class to make a Python property.

    NOTE: This one is not automatically extracted, but can be added to
          classes in the tweaker stage
    """
    def __init__(self, name, getter=None, setter=None, doc=None, **kw):
        super(PropertyDef, self).__init__()
        self.name = name
        self.getter = getter
        self.setter = setter
        self.briefDoc = doc
        self.protection = 'public'
        self.__dict__.update(kw)


class PyPropertyDef(PropertyDef):
    pass

#---------------------------------------------------------------------------

class CppMethodDef(MethodDef):
    """
    This class provides information that can be used to add the code for a new
    method to a wrapper class that does not actually exist in the real C++
    class, or it can be used to provide an alternate implementation for a
    method that does exist. The backend generator support for this feature
    would be things like %extend in SWIG or %MethodCode in SIP.

    NOTE: This one is not automatically extracted, but can be added to
          classes in the tweaker stage
    """
    def __init__(self, type, name, argsString, body, doc=None, isConst=False,
                 cppSignature=None, virtualCatcherCode=None, **kw):
        super(CppMethodDef, self).__init__()
        self.type = type
        self.name = name
        self.useDerivedName = True
        self.argsString = argsString
        self.body = body
        self.briefDoc = doc
        self.protection = 'public'
        self.klass = None
        self.noDerivedCtor = False
        self.isConst = isConst
        self.isPureVirtual = False
        self.cppSignature = cppSignature
        self.virtualCatcherCode = virtualCatcherCode
        self.isCore = _globalIsCore
        self.__dict__.update(kw)

    @staticmethod
    def FromMethod(method):
        """
        Create a new CppMethodDef that is essentially a copy of a MethodDef,
        so it can be used to write the code for a new wrapper function.

        TODO: It might be better to just refactor the code in the generator
        so it can be shared more easily intstead of using a hack like this...
        """
        m = CppMethodDef('', '', '', '')
        m.__dict__.update(method.__dict__)
        return m


class CppMethodDef_sip(CppMethodDef):
    """
    Just like the above, but instead of generating a new function from the
    provided code, the code is used inline inside SIP's %MethodCode directive.
    This makes it possible to use additional SIP magic for things that are
    beyond the general scope of the other C++ Method implementation.
    """
    pass

class CppMethodDef_cffi(MethodDef):
    """
    Like a CppMethodDef, but with the calling Python also provided by the user
    instead of generated automatically. This allows, among other things, custom
    conversion of arbitrary Python types into arbitrary C++ types.

    Note about parameter naming: *Args parameters expect a list while
    *ArgsString parameters expect a string.
    """
    def __init__(self,
        name, pyArgs, pyBody,
        cReturnType=None, cArgsString=None, cBody=None,
        originalCppType=None, originalCppArgs=None,
        virtualCReturnType=None, virtualCArgsString=None, virtualCBody=None,
        virtualPyArgs=None, virtualPyBody=None,
        *args, **kwargs):

        kwargs['name'] = name
        kwargs['type'] = 'void'
        super(CppMethodDef_cffi, self).__init__(*args, **kwargs)

        # Args list and body for the code Python that will be called by users
        # and is expected to call the corresponding C code. pyArgs should be a
        # list of ParamDef objects, where the type` is a C++ type the binding
        # generator is aware of or 'WL_Object'. In the latter case, no type
        # checking will be performed on the parameter and any Python object
        # will be accepted. The 'WL_Self' type must be used for a self
        # parameter.
        self.pyArgs = pyArgs
        self.pyBody = pyBody

        # Args string and body for the code C/C++ that will be called by Python
        # via CFFI. The cArgsString will be used in a cdef declaration, so it
        # must contain only types that CFFI can understand. If custom C/C++
        # code is specified, custom Python must also be specified. Also, when
        # custom C++ code is specified, any type that CFFI understands may be
        # used as a return type.
        self.cReturnType = cReturnType
        self.cArgsString = cArgsString
        self.cBody = cBody

        # The following attributes are necessary if the method is virtual. If
        # the method is a Ctor, originalCppArgs is optional. If it is given
        # and a subclass is being generated for the class, a Ctor with those
        # args will be included in the class.

        # Note that the binding generator must be able to understand all type
        # names used in the arguments list. This basically means that you will
        # not be able to use function pointers or templates without a typedef.
        self.originalCppType = originalCppType
        self.originalCppArgs = originalCppArgs

        # The following attributes are only required if the method is virtual

        # The return type and argument list specified here are passed to CFFI,
        # so only types that CFFI can understand may be used.
        self.virtualCReturnType = virtualCReturnType
        self.virtualCArgsString = virtualCArgsString
        self.virtualCBody = virtualCBody

        self.virtualPyArgs = virtualPyArgs
        self.virtualPyBody = virtualPyBody

#---------------------------------------------------------------------------

class WigCode(BaseDef):
    """
    This class allows code defined by the extractors to be injected into the
    generated Wrapper Interface Generator file. In other words, this is extra
    code meant to be consumed by the back-end code generator, and it will be
    injected at the point in the file generation that this object is seen.
    """
    def __init__(self, code, **kw):
        super(WigCode, self).__init__()
        self.code = code
        self.protection = 'public'
        self.__dict__.update(kw)

#---------------------------------------------------------------------------

class MappedTypeDef_cffi(BaseDef):
    def __init__(self, name, **kw):
        super(MappedTypeDef_cffi, self).__init__()
        self.name = name
        self.headerCode = []
        self.py2c = None
        self.c2cpp = None
        self.cpp2c = None
        self.c2py = None
        self.cType = None
        self.instanceCheck = None

        # placeholder is a dummy value used to support defaults. It should be
        # of the same type as cType and be inexpensive to create. For example,
        # if the cType is `long long`, 0 would be a fine value. The default is
        # `ffi.NULL` since it is assumed many mapped types will use pointers.
        self.placeHolder = 'ffi.NULL'
        self.__dict__.update(kw)


#---------------------------------------------------------------------------

class PyCodeDef(BaseDef):
    """
    This code held by this class will be written to a Python module
    that wraps the import of the extension module.
    """
    def __init__(self, code, order=None, **kw):
        super(PyCodeDef, self).__init__()
        self.code = code
        self.order = order
        self.__dict__.update(kw)


#---------------------------------------------------------------------------

class PyFunctionDef(BaseDef):
    """
    A PyFunctionDef can be used to define Python functions that will be
    written pretty much as-is to a module's .py file. Can also be used for
    methods in a PyClassDef. Using an explicit extractor object rather than
    just "including" the raw code lets us provide the needed metadata for
    document generators, etc.
    """
    def __init__(self, name, argsString, body, doc=None, order=None, **kw):
        super(PyFunctionDef, self).__init__()
        self.name = name
        self.argsString = self.pyArgsString = argsString
        self.body = body
        self.briefDoc = doc
        self.order = order
        self.deprecated = False
        self.isStatic = False
        self.overloads = []
        self.__dict__.update(kw)

#---------------------------------------------------------------------------

class PyClassDef(BaseDef):
    """
    A PyClassDef is used to define a pure-python class that will be injected
    into the module's .py file, but does so in a way that the various bits of
    information about the class are available in the extractor objects for
    the generators to use.
    """
    def __init__(self, name, bases=[], doc=None, items=[], order=None, **kw):
        super(PyClassDef, self).__init__()
        self.name = name
        self.bases = bases
        self.briefDoc = self.pyDocstring = doc
        self.enum_file = ''
        self.nodeBases = []
        self.subClasses = []
        self.items.extend(items)
        self.deprecated = False
        self.order = order
        self.__dict__.update(kw)

        self.nodeBases = self.findHierarchy()


    def findHierarchy(self):

        all_classes = {}
        nodename = fullname = self.name
        specials = [nodename]

        baselist = [base for base in self.bases if base != 'object']
        all_classes[nodename] = (nodename, fullname, baselist)

        for base in baselist:
            all_classes[base] = (base, base, [])

        return all_classes, specials


#---------------------------------------------------------------------------

class PyMethodDef(PyFunctionDef):
    """
    A PyMethodDef can be used to define Python class methods that will then be
    monkey-patched in to the extension module Types as if they belonged there.
    """
    def __init__(self, klass, name, argsString, body, doc=None, **kw):
        super(PyMethodDef, self).__init__(name, argsString, body, doc)
        self.klass = klass
        self.protection = 'public'
        self.__dict__.update(kw)

#---------------------------------------------------------------------------

class ModuleDef(BaseDef):
    """
    This class holds all the items that will be in the generated module
    """
    def __init__(self, package, module, name, docstring='', check4unittest=True):
        super(ModuleDef, self).__init__()
        self.package = package
        self.module = module
        self.name = name
        self.docstring = docstring
        self.check4unittest = check4unittest
        self.headerCode = []
        self.cppCode = []
        self.initializerCode = []
        self.preInitializerCode = []
        self.postInitializerCode = []
        self.includes = []
        self.imports = []

        self.cdefs_cffi = []


    def parseCompleted(self):
        """
        Called after the loading of items from the XML has completed, just
        before the tweaking stage is done.
        """

        # Reorder the items in the module to be a little more sane, such as
        # enums and other constants first, then the classes and functions (since
        # they may use those constants) and then the global variables, but perhaps
        # only those that have classes in this module as their type.
        one = list()
        two = list()
        three = list()
        for item in self.items:
            if isinstance(item, (ClassDef, FunctionDef)):
                two.append(item)
            elif isinstance(item, GlobalVarDef) and (
                     guessTypeInt(item) or guessTypeFloat(item) or guessTypeStr(item)):
                one.append(item)
            elif isinstance(item, GlobalVarDef):
                three.append(item)
            # template instantiations go at the end
            elif isinstance(item, TypedefDef) and '<' in item.type:
                three.append(item)

            else:
                one.append(item)
        self.items = one + two + three

        # give everything an isCore flag
        global _globalIsCore
        _globalIsCore = self.module == '_core'
        for item in self.allItems():
            item.isCore = _globalIsCore



    def addHeaderCode(self, code):
        if isinstance(code, list):
            self.headerCode.extend(code)
        else:
            self.headerCode.append(code)

    def addCppCode(self, code):
        if isinstance(code, list):
            self.cppCode.extend(code)
        else:
            self.cppCode.append(code)

    def includeCppCode(self, filename):
        self.addCppCode(textfile_open(filename).read())

    def addInitializerCode(self, code):
        if isinstance(code, list):
            self.initializerCode.extend(code)
        else:
            self.initializerCode.append(code)

    def addPreInitializerCode(self, code):
        if isinstance(code, list):
            self.preInitializerCode.extend(code)
        else:
            self.preInitializerCode.append(code)

    def addPostInitializerCode(self, code):
        if isinstance(code, list):
            self.postInitializerCode.extend(code)
        else:
            self.postInitializerCode.append(code)

    def addInclude(self, name):
        if isinstance(name, list):
            self.includes.extend(name)
        else:
            self.includes.append(name)

    def addImport(self, name):
        if isinstance(name, list):
            self.imports.extend(name)
        else:
            self.imports.append(name)


    def addElement(self, element):
        item = None
        kind = element.get('kind')
        if kind == 'class':
            extractingMsg(kind, element, ClassDef.nameTag)
            item = ClassDef(element, module=self)
            self.items.append(item)

        elif kind == 'struct':
            extractingMsg(kind, element, ClassDef.nameTag)
            item = ClassDef(element, kind='struct')
            self.items.append(item)

        elif kind == 'function':
            extractingMsg(kind, element)
            item = FunctionDef(element, module=self)
            if not item.checkForOverload(self.items):
                self.items.append(item)

        elif kind == 'enum':
            inClass = []
            for el in self.items:
                if isinstance(el, ClassDef):
                    inClass.append(el)

            extractingMsg(kind, element)
            item = EnumDef(element, inClass)
            self.items.append(item)

        elif kind == 'variable':
            extractingMsg(kind, element)
            item = GlobalVarDef(element)
            self.items.append(item)

        elif kind == 'typedef':
            extractingMsg(kind, element)
            item = TypedefDef(element)
            self.items.append(item)

        elif kind == 'define':
            # if it doesn't have a value, it must be a macro.
            value = flattenNode(element.find("initializer"))
            if not value:
                skippingMsg(kind, element)
            else:
                # NOTE: This assumes that the #defines are numeric values.
                # There will have to be some tweaking done for items that are
                # not numeric...
                extractingMsg(kind, element)
                item = DefineDef(element)
                self.items.append(item)

        elif kind == 'file' or kind == 'namespace':
            extractingMsg(kind, element)
            for node in element.findall('sectiondef/memberdef'):
                self.addElement(node)

        else:
            raise ExtractorError('Unknown module item kind: %s' % kind)

        return item



    def addCppFunction(self, type, name, argsString, body, doc=None, **kw):
        """
        Add a new C++ function into the module that is written by hand, not
        wrapped.
        """
        md = CppMethodDef(type, name, argsString, body, doc, **kw)
        self.items.append(md)
        return md


    def addCppFunction_sip(self, type, name, argsString, body, doc=None, **kw):
        """
        Add a new C++ function into the module that is written by hand, not
        wrapped.
        """
        md = CppMethodDef_sip(type, name, argsString, body, doc, **kw)
        self.items.append(md)
        return md


    def addPyCode(self, code, order=None):
        """
        Add a snippet of Python code to the wrapper module.
        """
        pc = PyCodeDef(code, order)
        self.items.append(pc)
        return pc


    def addGlobalStr(self, name, before=None):
        if self.findItem(name):
            self.findItem(name).ignore()
        gv = GlobalVarDef(type='const char*', name=name)
        if before is None:
            self.addItem(gv)
        else:
            self.insertItemBefore(before, gv)
        return gv


    def includePyCode(self, filename, order=None):
        """
        Add a snippet of Python code from a file to the wrapper module.
        """
        text = textfile_open(filename).read()
        return self.addPyCode(
            "#" + '-=' * 38 + '\n' +
            ("# This code block was included from %s\n%s\n" % (filename, text)) +
            "# End of included code block\n"
            "#" + '-=' * 38 + '\n'            ,
            order
            )


    def addPyFunction(self, name, argsString, body, doc=None, order=None, **kw):
        """
        Add a Python function to this module.
        """
        pf = PyFunctionDef(name, argsString, body, doc, order, **kw)
        self.items.append(pf)
        return pf


    def addPyClass(self, name, bases=[], doc=None, items=[], order=None, **kw):
        """
        Add a pure Python class to this module.
        """
        pc = PyClassDef(name, bases, doc, items, order, **kw)
        self.items.append(pc)
        return pc

    def addCdef_cffi(self, code):
        self.cdefs_cffi.append(code)



#---------------------------------------------------------------------------
# Some helper functions and such
#---------------------------------------------------------------------------

def flattenNode(node, rstrip=True):
    """
    Extract just the text from a node and its children, tossing out any child
    node tags and attributes.
    """
    if node is None:
        return ""
    if sys.version_info < (3,):
        strclass = basestring
    else:
        strclass = str
    if isinstance(node, strclass):
        return node
    text = node.text or ""
    for n in node:
        text += flattenNode(n, rstrip)
    if node.tail:
        text += node.tail
        if rstrip:
            text = text.rstrip()
    if rstrip:
        text = text.rstrip()
    return text


class ExtractorError(RuntimeError):
    pass


def _print(value, indent, stream):
    if stream is None:
        stream = sys.stdout
    indent = ' ' * indent
    for line in str(value).splitlines():
        stream.write("%s%s\n" % (indent, line))

def _pf(item, indent):
    if indent == 0:
        indent = 4
    txt =  pprint.pformat(item, indent)
    if '\n' in txt:
        txt = '\n' + txt
    return txt


def verbose():
    return '--verbose' in sys.argv

def extractingMsg(kind, element, nameTag='name'):
    if verbose():
        print('Extracting %s: %s' % (kind, element.find(nameTag).text))

def skippingMsg(kind, element):
    if verbose():
        print('Skipping %s: %s' % (kind, element.find('name').text))


class ArgsString(list):
    re_pattern = r'(?P<type>[a-zA-Z0-9_: ]+[ *&]+)(?P<name>[a-zA-Z0-9_]+)'
    re = re.compile(re_pattern)
    """
    Formating arguments strings:
    Parameters are only supported in the format of '<type-name> <parameter-
    name> [= <default-expersion>]'. Template and function pointers will not be
    parsed correctly. To use them, a typedef must first be created. WL_Object is
    a special type that can be used for arguments that should take non-type-
    checked Python object.
    """
    def __init__(self, argsstring):
        # Based heavily on extractors.FunctionDef.makePyArgsString
        super(ArgsString, self).__init__()

        # TODO: This breaks on functions calls in defaults.
        params = []
        args = argsstring.rsplit(')', 1)[0].strip('(').split(',')
        for arg in args:
            if not arg:
                continue
            param = ParamDef()
            self.append(param)

            # Is there a default value?
            if '=' in arg:
                param.default = arg.split('=')[1].strip()
                arg = arg.split('=')[0].strip()
            else:
                arg = arg.strip()
            # Now the last word should be the variable name, and everything
            # before it is the type
            type, name = self.re.match(arg).groups()

            param.type = type.strip()
            param.name = name.strip()

    def annt(self, param, annotation, value=True):
        if isinstance(param, int):
            param = self[param]
        elif isinstance(param, (unicode, str)):
            for p in self:
                if p.name == param:
                    param = p
                    break
            else:
                raise ValueError("no parameter named '%s' exists" % param)
        else:
            raise ValueError("got unexpected type '%s' for param" % type(param))


        if isinstance(annotation, (str, unicode)):
            setattr(param, annotation, value)
        elif isinstance(annotation, (list, tuple, set)):
            for a in annotation:
                setattr(param, a, value)
        elif isinstance(annotation, dict):
            for (key, value) in annotation.iteritems():
                setattr(param, key, value)
        else:
            raise ValueError("got unexpected type '%s' for annotation" %
                             type(annotation))

        return self


#---------------------------------------------------------------------------

