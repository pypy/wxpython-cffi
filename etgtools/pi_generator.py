#---------------------------------------------------------------------------
# Name:        etgtools/pi_generator.py
# Author:      Robin Dunn
#
# Created:     18-Oct-2011
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

"""
This generator will create "Python Interface" files, which define a skeleton
verison of the classes, functions, attributes, docstrings, etc. as Python
code. This is useful for enabling some introspcetion of things located in
extension modules where there is less information available for
introspection. The .pi files are used by WingIDE for assisting with code
completion, displaying docstrings in the source assistant panel, etc.
"""

import sys, os, re
import etgtools.extractors as extractors
import etgtools.generators as generators
from etgtools.generators import nci, Utf8EncodingStream, textfile_open
from etgtools.tweaker_tools import FixWxPrefix, magicMethods, \
                                   guessTypeInt, guessTypeFloat, guessTypeStr


phoenixRoot = os.path.abspath(os.path.split(__file__)[0]+'/..')

header = """\
# -*- coding: utf-8 -*-
#---------------------------------------------------------------------------
# This file is generated by wxPython's PI generator.  Do not edit by hand.
# 
# (The *.pi files are used by WingIDE to provide more information than it is 
# able to glean from introspection of extension types and methods.)
#
# Copyright: (c) 2013 by Total Control Software
# License:   wxWindows License
#---------------------------------------------------------------------------

"""

    
#---------------------------------------------------------------------------

class PiWrapperGenerator(generators.WrapperGeneratorBase, FixWxPrefix):
        
    def generate(self, module, destFile=None):
        stream = Utf8EncodingStream()
        
        # process the module object and its child objects
        self.generateModule(module, stream)
        
        # Write the contents of the stream to the destination file
        if not destFile:
            name = module.module + '.pi'
            if name.startswith('_'):
                name = name[1:]
            destFile = os.path.join(phoenixRoot, 'wx', name)
            
        if not os.path.exists(destFile):
            # create the file and write the header
            f = textfile_open(destFile, 'wt')
            f.write(header)
            f.close()
            
        self.writeSection(destFile, module.name, stream.getvalue())
            
        
    def writeSection(self, destFile, sectionName, sectionText):
        """
        Read all the lines from destFile, remove those currently between
        begin/end markers for sectionName (if any), and write the lines back
        to the file with the new text in sectionText.
        """
        sectionBeginLine = -1
        sectionEndLine = -1
        sectionBeginMarker = '#-- begin-%s --#' % sectionName
        sectionEndMarker = '#-- end-%s --#' % sectionName
        
        lines = textfile_open(destFile, 'rt').readlines()
        for idx, line in enumerate(lines):
            if line.startswith(sectionBeginMarker):
                sectionBeginLine = idx
            if line.startswith(sectionEndMarker):
                sectionEndLine = idx
                
        if sectionBeginLine == -1:
            # not there already, add to the end
            lines.append(sectionBeginMarker + '\n')
            lines.append(sectionText)
            lines.append(sectionEndMarker + '\n')
        else:
            # replace the existing lines
            lines[sectionBeginLine+1:sectionEndLine] = [sectionText]
            
        f = textfile_open(destFile, 'wt')
        f.writelines(lines)
        f.close()
        
        

    #-----------------------------------------------------------------------
    def generateModule(self, module, stream):
        """
        Generate code for each of the top-level items in the module.
        """
        assert isinstance(module, extractors.ModuleDef)
        self.isCore = module.module == '_core'
        
        for item in module.imports:
            if item.startswith('_'):
                item = item[1:]
            if item == 'core':
                continue
            stream.write('import wx.%s\n' % item)
        
        # Move all PyCode items with an order value to the begining of the
        # list as they most likely should appear before everything else.
        pycode = list()
        for item in module:
            if isinstance(item, extractors.PyCodeDef) and item.order is not None:
                pycode.append(item)
        for item in pycode:
            module.items.remove(item)
        module.items = pycode + module.items
                
        methodMap = {
            extractors.ClassDef         : self.generateClass,
            extractors.DefineDef        : self.generateDefine,
            extractors.FunctionDef      : self.generateFunction,
            extractors.EnumDef          : self.generateEnum,
            extractors.GlobalVarDef     : self.generateGlobalVar,
            extractors.TypedefDef       : self.generateTypedef,
            extractors.WigCode          : self.generateWigCode,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.PyFunctionDef    : self.generatePyFunction,
            extractors.PyClassDef       : self.generatePyClass,            
            extractors.CppMethodDef     : self.generateCppMethod,
            extractors.CppMethodDef_sip : self.generateCppMethod_sip,
            extractors.CppMethodDef_cffi: self.generateCppMethod_cffi,
            extractors.MappedTypeDef_cffi : lambda x, y: None,
            }
        
        for item in module:
            if item.ignored:
                continue
            function = methodMap[item.__class__]
            function(item, stream)

        
    #-----------------------------------------------------------------------
    def generateEnum(self, enum, stream, indent=''):
        assert isinstance(enum, extractors.EnumDef)
        if enum.ignored:
            return
        for v in enum.items:
            if v.ignored:
                continue
            name = v.pyName or v.name 
            stream.write('%s%s = 0\n' % (indent, name))
            
    #-----------------------------------------------------------------------
    def generateGlobalVar(self, globalVar, stream):
        assert isinstance(globalVar, extractors.GlobalVarDef)
        if globalVar.ignored:
            return
        name = globalVar.pyName or globalVar.name
        if guessTypeInt(globalVar):
            valTyp = '0'
        elif guessTypeFloat(globalVar):
            valTyp = '0.0'
        elif guessTypeStr(globalVar):
            valTyp = '""'
        else:
            valTyp = globalVar.type
            valTyp = valTyp.replace('const ', '')
            valTyp = valTyp.replace('*', '')
            valTyp = valTyp.replace('&', '')
            valTyp = valTyp.replace(' ', '')
            valTyp = self.fixWxPrefix(valTyp)
            valTyp += '()'
        
        stream.write('%s = %s\n' % (name, valTyp))
        
    #-----------------------------------------------------------------------
    def generateDefine(self, define, stream):
        assert isinstance(define, extractors.DefineDef)
        if define.ignored:
            return
        # we're assuming that all #defines that are not ignored are integer or string values
        if '"' in define.value:
            stream.write('%s = ""\n' % (define.pyName or define.name))
        else:
            stream.write('%s = 0\n' % (define.pyName or define.name))
        
    #-----------------------------------------------------------------------
    def generateTypedef(self, typedef, stream, indent=''):
        assert isinstance(typedef, extractors.TypedefDef)
        if typedef.ignored:
            return

        # If it's not a template instantiation, or has not been flagged by
        # the tweaker script that it should be treated as a class, then just
        # ignore the typedef and return.
        if not ('<' in typedef.type and '>' in typedef.type) and not typedef.docAsClass:
            return
        
        # Otherwise write a mock class for it that combines the template and class.
        # First, extract the info we need.
        if typedef.docAsClass:
            bases = [self.fixWxPrefix(b, True) for b in typedef.bases]
            name = self.fixWxPrefix(typedef.name)
            
        elif '<' in typedef.type and '>' in typedef.type:
            t = typedef.type.replace('>', '')
            t = t.replace(' ', '')
            bases = t.split('<')
            bases = [self.fixWxPrefix(b, True) for b in bases]
            name = self.fixWxPrefix(typedef.name)
            
        # Now write the Python equivallent class for the typedef
        if not bases:
            bases = ['object']  # this should not happpen, but just in case...
        stream.write('%sclass %s(%s):\n' % (indent, name, ', '.join(bases)))
        indent2 = indent + ' '*4
        if typedef.briefDoc:
            stream.write('%s"""\n' % indent2)
            stream.write(nci(typedef.briefDoc, len(indent2)))
            stream.write('%s"""\n' % indent2)
        else:
            stream.write('%spass\n\n' % indent2)


    #-----------------------------------------------------------------------
    def generateWigCode(self, wig, stream, indent=''):
        assert isinstance(wig, extractors.WigCode)
        # write nothing for this one
        
        
    #-----------------------------------------------------------------------
    def generatePyCode(self, pc, stream, indent=''):
        assert isinstance(pc, extractors.PyCodeDef)
        code = pc.code
        if hasattr(pc, 'klass'):
            code = code.replace(pc.klass.pyName+'.', '') 
        stream.write('\n')
        stream.write(nci(code, len(indent)))

    #-----------------------------------------------------------------------
    def generatePyFunction(self, pf, stream, indent=''):
        assert isinstance(pf, extractors.PyFunctionDef)
        stream.write('\n')
        if pf.deprecated:
            stream.write('%s@wx.deprecated\n' % indent)  
        if pf.isStatic:
            stream.write('%s@staticmethod\n' % indent)  
        stream.write('%sdef %s%s:\n' % (indent, pf.name, pf.argsString))
        indent2 = indent + ' '*4
        if pf.briefDoc:
            stream.write('%s"""\n' % indent2)
            stream.write(nci(pf.briefDoc, len(indent2)))
            stream.write('%s"""\n' % indent2)
        stream.write('%spass\n' % indent2)
        
    #-----------------------------------------------------------------------
    def generatePyClass(self, pc, stream, indent=''):
        assert isinstance(pc, extractors.PyClassDef)
    
        # write the class declaration and docstring
        if pc.deprecated:
            stream.write('%s@wx.deprecated\n' % indent)
        stream.write('%sclass %s' % (indent, pc.name))
        if pc.bases:
            stream.write('(%s):\n' % ', '.join(pc.bases))
        else:
            stream.write('(object):\n')
        indent2 = indent + ' '*4
        if pc.briefDoc:
            stream.write('%s"""\n' % indent2)
            stream.write(nci(pc.briefDoc, len(indent2)))
            stream.write('%s"""\n' % indent2)

        # these are the only kinds of items allowed to be items in a PyClass
        dispatch = {
            extractors.PyFunctionDef    : self.generatePyFunction,
            extractors.PyPropertyDef    : self.generatePyProperty,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.PyClassDef       : self.generatePyClass,
        }
        for item in pc.items:
            item.klass = pc
            f = dispatch[item.__class__]
            f(item, stream, indent2)



    #-----------------------------------------------------------------------
    def generateFunction(self, function, stream):
        assert isinstance(function, extractors.FunctionDef)
        if not function.pyName:
            return
        stream.write('\ndef %s' % function.pyName)
        if function.overloads:
            stream.write('(*args, **kw)')
        else:
            argsString = function.pyArgsString
            if not argsString:
                argsString = '()'
            if '->' in argsString:
                pos = argsString.find(')')
                argsString = argsString[:pos+1]
            if '(' != argsString[0]:
                pos = argsString.find('(')
                argsString = argsString[pos:]
            argsString = argsString.replace('::', '.')
            stream.write(argsString)
        stream.write(':\n')
        stream.write('    """\n')
        stream.write(nci(function.pyDocstring, 4))
        stream.write('    """\n')
        
        
    def generateParameters(self, parameters, stream, indent):
        def _lastParameter(idx):
            if idx == len(parameters)-1:
                return True
            for i in range(idx+1, len(parameters)):
                if not parameters[i].ignored:
                    return False
            return True
                
        for idx, param in enumerate(parameters):
            if param.ignored:
                continue
            stream.write(param.name)
            if param.default:
                stream.write('=%s' % param.default)
            if not _lastParameter(idx):
                stream.write(', ')
                
                
    #-----------------------------------------------------------------------
    def generateClass(self, klass, stream, indent=''):
        assert isinstance(klass, extractors.ClassDef)
        if klass.ignored:
            return
        
        # check if there is a pi-customized version of the base class names
        if hasattr(klass, 'piBases'):
            bases = klass.piBases
            
        else:
            # check if it's a template with the template parameter as the base class
            bases = klass.bases[:]
            for tp in klass.templateParams:
                if tp in bases:
                    bases.remove(tp)
        
        # write class declaration
        klassName = klass.pyName or klass.name
        stream.write('\n%sclass %s' % (indent, klassName))
        if bases:
            stream.write('(')
            bases = [self.fixWxPrefix(b, True) for b in bases]
            stream.write(', '.join(bases))
            stream.write(')')
        else:
            stream.write('(object)')
        stream.write(':\n')
        indent2 = indent + ' '*4
        
        # docstring
        stream.write('%s"""\n' % indent2)
        stream.write(nci(klass.pyDocstring, len(indent2)))
        stream.write('%s"""\n' % indent2)
        
        # generate nested classes
        for item in klass.innerclasses:
            self.generateClass(item, stream, indent2)
            
        # Split the items into public and protected groups
        enums = [i for i in klass if 
                     isinstance(i, extractors.EnumDef) and 
                     i.protection == 'public']
        ctors = [i for i in klass if 
                     isinstance(i, extractors.MethodDef) and 
                     i.protection == 'public' and (i.isCtor or i.isDtor)]
        public = [i for i in klass if i.protection == 'public' and 
                     i not in ctors and i not in enums]
        protected = [i for i in klass if i.protection == 'protected']

        dispatch = {
            extractors.MemberVarDef     : self.generateMemberVar,
            extractors.PropertyDef      : self.generateProperty,
            extractors.PyPropertyDef    : self.generatePyProperty,
            extractors.MethodDef        : self.generateMethod,
            extractors.EnumDef          : self.generateEnum,
            extractors.CppMethodDef     : self.generateCppMethod,
            extractors.CppMethodDef_sip : self.generateCppMethod_sip,
            extractors.CppMethodDef_cffi: self.generateCppMethod_cffi,
            extractors.PyMethodDef      : self.generatePyMethod,
            extractors.PyCodeDef        : self.generatePyCode,
            extractors.WigCode          : self.generateWigCode,
            }

        for item in enums:
            item.klass = klass
            self.generateEnum(item, stream, indent2)

        for item in ctors: 
            if item.isCtor:
                item.klass = klass
                self.generateMethod(item, stream, indent2, 
                                    name='__init__', docstring=klass.pyDocstring)

        for item in public:
            item.klass = klass
            f = dispatch[item.__class__]
            f(item, stream, indent2)
            
        for item in protected:
            item.klass = klass
            f = dispatch[item.__class__]
            f(item, stream, indent2)

        stream.write('%s# end of class %s\n\n' % (indent, klassName))
        
        
    def generateMemberVar(self, memberVar, stream, indent):
        assert isinstance(memberVar, extractors.MemberVarDef)
        if memberVar.ignored:
            return
        stream.write('%s%s = property(None, None)\n' % (indent, memberVar.name))


    def generateProperty(self, prop, stream, indent):
        assert isinstance(prop, extractors.PropertyDef)
        if prop.ignored:
            return
        stream.write('%s%s = property(None, None)\n' % (indent, prop.name))


    def generatePyProperty(self, prop, stream, indent):
        assert isinstance(prop, extractors.PyPropertyDef)
        if prop.ignored:
            return
        stream.write('%s%s = property(None, None)\n' % (indent, prop.name))


    def generateMethod(self, method, stream, indent, name=None, docstring=None):
        assert isinstance(method, extractors.MethodDef)
        for m in method.all():  # use the first not ignored if there are overloads
            if not m.ignored:
                method = m
                break
        else:
            return
        if method.isDtor:
            return
        
        name = name or method.pyName or method.name
        if name in magicMethods:
            name = magicMethods[name]

        # write the method declaration
        if method.isStatic:
            stream.write('\n%s@staticmethod' % indent)
        stream.write('\n%sdef %s' % (indent, name))
        if method.overloads:
            if not method.isStatic:
                stream.write('(self, *args, **kw)')
            else:
                stream.write('(*args, **kw)')
        else:
            argsString = method.pyArgsString
            if not argsString:
                argsString = '()'
            if '->' in argsString:
                pos = argsString.find(') ->')
                argsString = argsString[:pos+1]
            if '(' != argsString[0]:
                pos = argsString.find('(')
                argsString = argsString[pos:]
            if not method.isStatic:
                if argsString == '()':
                    argsString = '(self)'
                else:
                    argsString = '(self, ' + argsString[1:]
            argsString = argsString.replace('::', '.')
            stream.write(argsString)
        stream.write(':\n')
        indent2 = indent + ' '*4
        
        # docstring
        if not docstring:
            if hasattr(method, 'pyDocstring'):
                docstring = method.pyDocstring
            else:
                docstring = ""
        stream.write('%s"""\n' % indent2)
        if docstring.strip():
            stream.write(nci(docstring, len(indent2)))
        stream.write('%s"""\n' % indent2)
        
        

    def generateCppMethod(self, method, stream, indent=''):
        assert isinstance(method, extractors.CppMethodDef)
        self.generateMethod(method, stream, indent)


    def generateCppMethod_sip(self, method, stream, indent=''):
        assert isinstance(method, extractors.CppMethodDef_sip)
        self.generateMethod(method, stream, indent)

    def generateCppMethod_cffi(self, method, stream, indent=''):
        assert isinstance(method, extractors.CppMethodDef_cffi)
        self.generateMethod(method, stream, indent)
        

    def generatePyMethod(self, pm, stream, indent):
        assert isinstance(pm, extractors.PyMethodDef)
        if pm.ignored:
            return
        if pm.isStatic:
            stream.write('\n%s@staticmethod' % indent)
        stream.write('\n%sdef %s' % (indent, pm.name))
        stream.write(pm.argsString)
        stream.write(':\n')
        indent2 = indent + ' '*4

        stream.write('%s"""\n' % indent2)
        stream.write(nci(pm.pyDocstring, len(indent2)))
        stream.write('%s"""\n' % indent2)
   
        
        
        
#---------------------------------------------------------------------------
#---------------------------------------------------------------------------
