#---------------------------------------------------------------------------
# Name:        etgtools/tweaker_tools.py
# Author:      Robin Dunn
#
# Created:     3-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

"""
Some helpers and utility functions that can assist with the tweaker
stage of the ETG scripts.
"""

import etgtools as extractors
from .generators import textfile_open, runGeneratorSpecificScript, getGenerator
import sys, os
import copy


PY3 = sys.version_info[0] == 3

magicMethods = {
    'operator!='    : '__ne__',
    'operator=='    : '__eq__',
    'operator<'     : '__lt__',
    'operator<='    : '__le__',
    'operator>'     : '__gt__',
    'operator>='    : '__ge__',
    'operator+'     : '__add__',
    'operator-'     : '__sub__',
    'operator*'     : '__mul__',
    'operator/'     : '__div__',
    'operator+='    : '__iadd__',
    'operator-='    : '__isub__',
    'operator*='    : '__imul__',
    'operator/='    : '__idiv__',
    'operator bool' : '__int__',  # Why not __nonzero__?
    # TODO: add more
}


def removeWxPrefixes(node):
    """
    Rename items with a 'wx' prefix to not have the prefix. If the back-end
    generator supports auto-renaming then it can ignore the pyName value for
    those that are changed here. We'll still change them all incase the
    pyNames are needed elsewhere.
    """
    for item in node.allItems():
        if not item.pyName \
           and item.name.startswith('wx') \
           and not item.name.startswith('wxEVT_') \
           and not isinstance(item, (extractors.TypedefDef,
                                     extractors.MethodDef )):  # TODO: Any others?
                item.pyName = item.name[2:]
                item.wxDropped = True
        if item.name.startswith('wxEVT_') and 'CATEGORY' not in item.name:
            # give these their actual name so the auto-renamer won't touch them
            item.pyName = item.name
            

def removeWxPrefix(name):
    if name.startswith('wx.') or name.startswith('``wx.'):
        return name
    
    if name.startswith('wx') and not name.startswith('wxEVT_'):
        name = name[2:]
    
    if name.startswith('``wx') and not name.startswith('``wxEVT_'):
        name = name[0:2] + name[4:]
        
    return name




class FixWxPrefix(object):
    """
    A mixin class that can help with removing the wx prefix, or changing it
    in to a "wx.Name" depending on where it is being used from.
    """
    
    _coreTopLevelNames = None
    
    def fixWxPrefix(self, name, checkIsCore=False):
        # By default remove the wx prefix like normal
        name = removeWxPrefix(name)
        if not checkIsCore or self.isCore:
            return name
        
        # Otherwise, if we're not processing the core module currently then check
        # if the name is local or if it resides in core. If it does then return
        # the name as 'wx.Name'
        if FixWxPrefix._coreTopLevelNames is None:
            self._getCoreTopLevelNames()
            
        testName = name
        if '(' in name:
            testName = name[:name.find('(')]
            
        if testName in FixWxPrefix._coreTopLevelNames:
            return 'wx.'+name
        else:
            return name


    def _getCoreTopLevelNames(self):
        # Since the real wx.core module may not exist yet, and since actually
        # executing code at this point is probably a bad idea, try parsing the
        # core.pi file and pulling the top level names from it.
        import ast

        def _processItem(item, names):
            if isinstance(item, ast.Assign):
                for t in item.targets:
                    _processItem(t, names)
            elif isinstance(item, ast.Name):
                names.append(item.id)
            elif isinstance(item, ast.ClassDef):
                names.append(item.name)
            elif isinstance(item, ast.FunctionDef):
                names.append(item.name)
        
        names = list()
        filename = 'wx/core.pi'
        if PY3:
            with open(filename, 'rt', encoding='utf-8') as f:
                text = f.read()
        else:
            with open(filename, 'r') as f:
                text = f.read()
        parseTree = ast.parse(text, filename)
        for item in parseTree.body:
            _processItem(item, names)

        FixWxPrefix._coreTopLevelNames = names
        
    


def ignoreAssignmentOperators(node):
    """
    Set the ignored flag for all class methods that are assignment operators
    """
    for item in node.allItems():
        if (isinstance(item, extractors.MethodDef) and item.name == 'operator='
            and item.protection != 'private'):
            item.ignore()

            
def ignoreAllOperators(node):
    """
    Set the ignored flag for all class methods that are any kind of operator
    """
    for item in node.allItems():
        if isinstance(item, extractors.MethodDef) and item.name.startswith('operator'):
            item.ignore()


def ignoreConstOverloads(node):
    """
    If a method is overloaded and one of them only differs by const-ness,
    then ignore it.
    """
    def _checkOverloads(item):
        overloads = item.all()
        for i in range(len(overloads)):
            for j in range(len(overloads)):
                if i == j:
                    continue
                item1 = overloads[i]
                item2 = overloads[j]
                if item1.ignored or item2.ignored:
                    continue
                if (item1.argsString.replace(' const', '').strip() == 
                    item2.argsString.replace(' const', '').strip()):
                    if item1.isConst:
                        item1.ignore()
                        return
                    elif item2.isConst:
                        item2.ignore()
                        return
        
    for item in node.items:
        if isinstance(item, extractors.MethodDef) and item.overloads:
            _checkOverloads(item)
            
            
            
def addAutoProperties(node):
    """
    Call klass.addAutoProperties for all classes in node with
    allowAutoProperties set and which do not already have properties added by
    hand in the tweaker code.
    """
    for item in node.allItems():
        if isinstance(item, extractors.ClassDef):
            if not item.allowAutoProperties:
                continue
            if len([i for i in item if isinstance(i, extractors.PropertyDef)]):
                continue
            item.addAutoProperties()

            
def fixEventClass(klass, ignoreProtected=True):
    """
    Add the extra stuff that an event class needs that are lacking from the
    interface headers.
    """
    assert isinstance(klass, extractors.ClassDef)
    if klass.name != 'wxEvent':
        # Clone() in wxEvent is pure virtual, so we need to let the back-end
        # know that the other event classes have an implementation for it so
        # it won't think that they are abstract classes too.
        if not klass.findItem('Clone'):
            klass.addPublic('virtual wxEvent* Clone() const /Factory/;')

    # Add a private assignment operator so the back-end (if it's watching out
    # for this) won't try to make copies by assignment.
    klass.addPrivateAssignOp()

    if not ignoreProtected:
        for item in klass.allItems():
            if isinstance(item, extractors.MethodDef) and item.protection == 'protected':
                item.ignore(False)
        

    
def fixWindowClass(klass, hideVirtuals=True, ignoreProtected=True):
    """
    Do common tweaks for a window class.
    """
    # The ctor and Create method transfer ownership of the this pointer
    for func in klass.findAll(klass.name) + klass.findAll('Create'):
        if isinstance(func, extractors.MethodDef):
            # if a class has an empty ctor it might not have this
            parent = func.findItem('parent')
            if parent:
                parent.transferThis = True
            # give the id param a default value if it has one
            id = func.findItem('id') or func.findItem('winid')
            if id:
                id.default = 'wxID_ANY'

            # if there is a pos or size parameter without a default then give it one.
            p = func.findItem('pos')
            if p and not p.default:
                p.default = 'wxDefaultPosition'
            p = func.findItem('size')
            if p and not p.default:
                p.default = 'wxDefaultSize'

    if hideVirtuals:
        # There is no need to make all the C++ virtuals overridable in Python, and
        # hiding the fact that they are virtual from the back end generator will
        # greatly reduce the amount of code that needs to be generated. Remove all
        # the virtual flags, and then add it back to a select few.
        removeVirtuals(klass)
        addWindowVirtuals(klass)

    if not ignoreProtected:
        for item in klass.allItems():
            if isinstance(item, extractors.MethodDef) and item.protection == 'protected':
                item.ignore(False)
        
        
    
def fixTopLevelWindowClass(klass, hideVirtuals=True, ignoreProtected=True):
    """
    Tweaks for TLWs 
    """
    # TLW tweaks are a little different. We use the function annotation for
    # TransferThis instead of the argument anotation.
    klass.find(klass.name).findOverload('parent').transfer = True
    item = klass.findItem('Create')
    if item:
        item.transferThis = True
        
    # give the id param a default value
    for item in [klass.findItem('%s.id' % klass.name), klass.findItem('Create.id')]:
        if item:
            item.default = 'wxID_ANY'

    # give title param a default too if it needs it
    for item in [klass.findItem('%s.title' % klass.name), klass.findItem('Create.title')]:
        if item and not item.default:
            item.default = 'wxEmptyString'

    if hideVirtuals:
        removeVirtuals(klass)
        addWindowVirtuals(klass)
    
    if not ignoreProtected:
        for item in klass.allItems():
            if isinstance(item, extractors.MethodDef) and item.protection == 'protected':
                item.ignore(False)
    
    
    
def fixSizerClass(klass):
    """
    Remove all virtuals except for CalcMin and RecalcSizes.
    """
    removeVirtuals(klass)
    klass.find('CalcMin').isVirtual = True
    klass.find('RecalcSizes').isVirtual = True
    
    # in the wxSizer class they are pure-virtual
    if klass.name == 'wxSizer':
        klass.find('CalcMin').isPureVirtual = True
        klass.find('RecalcSizes').isPureVirtual = True
    
    
def fixBookctrlClass(klass, treeBook=False):
    """
    Add declarations of the pure virtual methods from the base class.
    """    
    klass.addItem(extractors.WigCode("""\
        virtual int GetPageImage(size_t nPage) const;
        virtual bool SetPageImage(size_t page, int image);
        virtual wxString GetPageText(size_t nPage) const;
        virtual bool SetPageText(size_t page, const wxString& text);
        virtual int SetSelection(size_t page);
        virtual int ChangeSelection(size_t page);
        """))
    if not treeBook:
        klass.addItem(extractors.WigCode("""\
        virtual int GetSelection() const;
        virtual bool InsertPage(size_t index, wxWindow * page, const wxString & text,
                                bool select = false, int imageId = NO_IMAGE);
        """))

    
def fixHtmlSetFonts(klass):
    # Use wxArrayInt instead of a C array of ints.
    m = klass.find('SetFonts')
    m.find('sizes').type = 'const wxArrayInt&'
    m.find('sizes').default = ''
    m.argsString = '(const wxString & normal_face, const wxString & fixed_face, const wxArrayInt& sizes)'
    m.setCppCode("""\
        if (sizes->GetCount() != 7) {
            wxPyErr_SetString(PyExc_ValueError, "Sequence of 7 integers expected.");
            return;
        }
        self->SetFonts(*normal_face, *fixed_face, &sizes->Item(0));
        """)
    

def removeVirtuals(klass):
    """
    Sometimes methods are marked as virtual but probably don't ever need to be
    overridden from Python. This function will unset the virtual flag for all
    methods in a class, which can save some code-bloat in the wrapper code.
    """
    assert isinstance(klass, extractors.ClassDef)
    for item in klass.allItems():
        if isinstance(item, extractors.MethodDef):
            item.isVirtual = item.isPureVirtual = False

            
def addWindowVirtuals(klass):
    """
    Either turn the virtual flag back on or add a delcaration for the subset of
    the C++ virtuals in wxWindow classes that we will be supporting.
    """
    type = 'type'
    name = 'name'
    argsString = 'argsString'
    items = 'items'
    isConst = 'isConst'
    publicWindowVirtuals = [
        #('GetClientAreaOrigin',      'wxPoint GetClientAreaOrigin() const'),
        #('Validate',                 'bool Validate()'),
        #('TransferDataToWindow',     'bool TransferDataToWindow()'),
        #('TransferDataFromWindow',   'bool TransferDataFromWindow()'),
        #('InitDialog',               'void InitDialog()'),
        #('AcceptsFocus',             'bool AcceptsFocus() const'),
        #('AcceptsFocusRecursively',  'bool AcceptsFocusRecursively() const'),
        #('AcceptsFocusFromKeyboard', 'bool AcceptsFocusFromKeyboard() const'),
        #('AddChild',                 'void AddChild( wxWindowBase *child )'),
        #('RemoveChild',              'void RemoveChild( wxWindowBase *child )'),
        #('InheritAttributes',        'void InheritAttributes()'),
        #('ShouldInheritColours',     'bool ShouldInheritColours() const'),
        #('OnInternalIdle',           'void OnInternalIdle()'),
        #('GetMainWindowOfCompositeControl', 
        #                             'wxWindow *GetMainWindowOfCompositeControl()'),
        #('InformFirstDirection',     'bool InformFirstDirection(int direction, int size, int availableOtherDir)'),
        #('SetCanFocus',              'void SetCanFocus(bool canFocus)'),
        
        ## What about these?
        #bool HasMultiplePages() const 
        #void UpdateWindowUI(long flags = wxUPDATE_UI_NONE);
        #void DoUpdateWindowUI(wxUpdateUIEvent& event) ;

        {type: 'wxPoint', name: 'GetClientAreaOrigin', argsString: '()', isConst: True},
        {type: 'bool', name: 'Validate', argsString: '()'},
        {type: 'bool', name: 'TransferDataToWindow', argsString: '()'},
        {type: 'bool', name: 'TransferDataFromWindow', argsString: '()'},
        {type: 'void', name: 'InitDialog', argsString: '()'},
        {type: 'bool', name: 'AcceptsFocus', argsString: '()', isConst: True},
        {type: 'bool', name: 'AcceptsFocusRecursively', argsString: '()', isConst: True},
        {type: 'bool', name: 'AcceptsFocusFromKeyboard', argsString: '()', isConst: True},
        {type: 'void', name: 'AddChild', argsString: '( wxWindowBase *child )'},
        {type: 'void', name: 'RemoveChild', argsString: '( wxWindowBase *child )'},
        {type: 'void', name: 'InheritAttributes', argsString: '()'},
        {type: 'bool', name: 'ShouldInheritColours', argsString: '()', isConst: True},
        {type: 'void', name: 'OnInternalIdle', argsString: '()'},
        {type: 'wxWindow*', name: 'GetMainWindowOfCompositeControl', argsString: '()'},
        {type: 'bool', name: 'InformFirstDirection', argsString: '(int direction, int size, int availableOtherDir)'},
        {type: 'void', name: 'SetCanFocus', argsString: '(bool canFocus)'},
    ]
    
    protectedWindowVirtuals = [    
        #('ProcessEvent',              'bool ProcessEvent(wxEvent & event)'),
        #('DoEnable',                  'void DoEnable(bool enable)'),
        #('DoGetPosition',             'void DoGetPosition(int *x, int *y) const'),
        #('DoGetSize',                 'void DoGetSize(int *width, int *height) const'),
        #('DoGetClientSize',           'void DoGetClientSize(int *width, int *height) const'),
        #('DoGetBestSize',             'wxSize DoGetBestSize() const'),
        #('DoGetBestClientSize',       'wxSize DoGetBestClientSize() const'),
        #('DoSetSize',                 'void DoSetSize(int x, int y, int width, int height, int sizeFlags)'),
        #('DoSetClientSize',           'void DoSetClientSize(int width, int height)'),
        #('DoSetSizeHints',            'void DoSetSizeHints( int minW, int minH, int maxW, int maxH, int incW, int incH )'),
        #('DoGetBorderSize',           'wxSize DoGetBorderSize() const'),
        #('DoMoveWindow',              'void DoMoveWindow(int x, int y, int width, int height)'),
        #('DoSetWindowVariant',        'void DoSetWindowVariant( wxWindowVariant variant)'),
        #('GetDefaultBorder',          'wxBorder GetDefaultBorder() const'),
        #('GetDefaultBorderForControl','wxBorder GetDefaultBorderForControl() const'),
        #('DoFreeze',                  'void DoFreeze()'),
        #('DoThaw',                    'void DoThaw()'),
        #('HasTransparentBackground',  'bool HasTransparentBackground()'),

        ## What about these?
        #('DoGetScreenPosition', 'void DoGetScreenPosition(int *x, int *y) const'),
        #('DoSetVirtualSize',    'void DoSetVirtualSize( int x, int y )'),
        #('DoGetVirtualSize',    'wxSize DoGetVirtualSize() const'),
        {type: 'bool', name: 'ProcessEvent', argsString: '(wxEvent & event)'},
        {type: 'void', name: 'DoEnable', argsString: '(bool enable)'},
        {type: 'void', name: 'DoGetPosition', argsString: '(int *x, int *y)', isConst: True},
        {type: 'void', name: 'DoGetSize', argsString: '(int *width, int *height)', isConst: True},
        {type: 'void', name: 'DoGetClientSize', argsString: '(int *width, int *height)', isConst: True},
        {type: 'wxSize', name: 'DoGetBestSize', argsString: '()', isConst: True},
        {type: 'wxSize', name: 'DoGetBestClientSize', argsString: '()', isConst: True},
        {type: 'void', name: 'DoSetSize', argsString: '(int x, int y, int width, int height, int sizeFlags)'},
        {type: 'void', name: 'DoSetClientSize', argsString: '(int width, int height)'},
        {type: 'void', name: 'DoSetSizeHints', argsString: '( int minW, int minH, int maxW, int maxH, int incW, int incH )'},
        {type: 'wxSize', name: 'DoGetBorderSize', argsString: '()', isConst: True},
        {type: 'void', name: 'DoMoveWindow', argsString: '(int x, int y, int width, int height)'},
        {type: 'void', name: 'DoSetWindowVariant', argsString: '( wxWindowVariant variant)'},
        {type: 'wxBorder', name: 'GetDefaultBorder', argsString: '()', isConst: True},
        {type: 'wxBorder', name: 'GetDefaultBorderForControl', argsString: '()', isConst: True},
        {type: 'void', name: 'DoFreeze', argsString: '()'},
        {type: 'void', name: 'DoThaw', argsString: '()'},
        {type: 'bool', name: 'HasTransparentBackground', argsString: '()'},
    ]
    
    def _processItems(klass, prot, virtuals):
        for meth in virtuals:
            m = klass.findItem(meth['name'])
            if m:
                m.ignore(False)
                m.isVirtual = True
            else:
                klass.addMethod(isVirtual=True, protection=prot, **meth)
    
    _processItems(klass, 'public', publicWindowVirtuals)
    _processItems(klass, 'protected', protectedWindowVirtuals)
                  
                  
def addSipConvertToSubClassCode(klass):
    """
    Teach SIP how to convert to specific subclass types
    """
    klass.addItem(extractors.WigCode("""\
    %ConvertToSubClassCode
        const wxClassInfo* info   = sipCpp->GetClassInfo();
        wxString           name   = info->GetClassName();
        bool               exists = sipFindType(name) != NULL;
        while (info && !exists) {
            info = info->GetBaseClass1();
            name = info->GetClassName();
            exists = sipFindType(name) != NULL;
        }
        if (info) 
            sipType = sipFindType(name);
        else
            sipType = NULL;
    %End
    """))

def addCffiConvertToSubClassCode(klass):
    klass.detectSubclassCode_cffi = """\
    const wxClassInfo* info = cpp_obj->GetClassInfo();
    wxString name = info->GetClassName();

    return wxStrdup(name);
    """
    
    
def getEtgFiles(names):
    """
    Create a list of the files from the basenames in the names list that
    corespond to files in the etg folder.
    """
    globalPattern = os.path.join('etg', '%s.py')
    specificPattern = os.path.join('etg', getGenerator(), '%s.py')

    globalEtgFiles = getMatchingFiles(names, globalPattern)

    gendir = getGenerator()
    specificEtgFiles = []
    for name in names:
        globalName = globalPattern % name
        specificName = specificPattern % name
        if not os.path.exists(globalName) and os.path.exists(specificName):
            specificEtgFiles.append(specificName)

    return globalEtgFiles + specificEtgFiles


def getNonEtgFiles(names, template='src/%s.sip'):
    """
    Get the files other than the ETG scripts from the list of names that match
    the template. By default gets the SIP files in src.
    """
    return getMatchingFiles(names, template)

    
def getMatchingFiles(names, template):
    """
    Create a list of files from the basenames in names that match the template
    and actually exist.
    """
    files = list()
    for name in names:
        name = template % name
        if os.path.exists(name):
            files.append(name)
    return files
            

            
def doCommonTweaks(module):
    """
    A collection of tweaks that should probably be done to all modules.
    """
    ignoreAssignmentOperators(module)
    removeWxPrefixes(module)
    addAutoProperties(module)
    
    
def changeTypeNames(module, oldName, newName, skipTypedef=False):
    """
    Changes the matching type names for functions and parameters to a new
    name, and optionally adds typedefs for the new name as well.
    """
    if not skipTypedef:
        module.addHeaderCode("typedef {old} {new};".format(old=oldName, new=newName))
        module.addItem(extractors.TypedefDef(type=oldName, name=newName))
    for item in module.allItems():
        if isinstance(item, (extractors.FunctionDef, extractors.ParamDef)) and \
                 hasattr(item, 'type') and oldName in item.type:
            item.type = item.type.replace(oldName, newName)



def copyClassDef(klass, newName):
    """
    Make a copy of a class object and give it a new name.
    """
    oldName = klass.name
    klass = copy.deepcopy(klass)
    assert isinstance(klass, extractors.ClassDef)
    klass.name = newName
    for ctor in klass.find(oldName).all():
        ctor.name = newName
    if klass.findItem('~'+oldName):
        klass.find('~'+oldName).name = '~'+newName
    return klass

#---------------------------------------------------------------------------


def getWrapperGenerator():
    """
    A simple factory function to create a wrapper generator class of the desired type.
    """
    if '--swig' in sys.argv:
        from etgtools import swig_generator
        gClass = swig_generator.SwigWrapperGenerator
    elif '--sip' in sys.argv:
        from etgtools import sip_generator
        gClass = sip_generator.SipWrapperGenerator
    elif '--cffi'  in sys.argv:
        from etgtools import cffi_generator
        gClass = cffi_generator.CffiWrapperGenerator
    else:
        # The default is sip
        from etgtools import sip_generator
        gClass = sip_generator.SipWrapperGenerator    
    return gClass()


def getDocsGenerator():
    if '--nodoc' in sys.argv:
        from etgtools import generators    
        return generators.StubbedDocsGenerator()
    elif '--sphinx' in sys.argv:
        from etgtools import sphinx_generator
        return sphinx_generator.SphinxGenerator()
    else:
        # the current default is sphinx
        from etgtools import sphinx_generator
        return sphinx_generator.SphinxGenerator()
        


def runGenerators(module):
    checkForUnitTestModule(module)

    generators = list()
    
    # Create the code generator selected from command line args
    generators.append(getWrapperGenerator())
    
    # Toss in the PI generator too
    from etgtools import pi_generator
    generators.append(pi_generator.PiWrapperGenerator())
    
    # And finally add the documentation generator
    generators.append(getDocsGenerator())

    # run the generators
    for g in generators:
        g.generate(module)
        


def checkForUnitTestModule(module):
    pathname = 'unittests/test_%s.py' % module.name
    if os.path.exists(pathname) or not module.check4unittest:
        return
    print('WARNING: Unittest module (%s) not found!' % pathname)


#---------------------------------------------------------------------------


def convertTwoIntegersTemplate(CLASS):
    # Note: The GIL is already acquired where this code is used.
    return """\
   // is it just a typecheck?
   if (!sipIsErr) {{
       // is it already an instance of {CLASS}?
       if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS))
           return 1;

       if (PySequence_Check(sipPy) && PySequence_Size(sipPy) == 2) {{
           int rval = 1;
           PyObject* o1 = PySequence_ITEM(sipPy, 0);
           PyObject* o2 = PySequence_ITEM(sipPy, 1);
           if (!PyNumber_Check(o1) || !PyNumber_Check(o2)) 
               rval = 0;
           Py_DECREF(o1);
           Py_DECREF(o2);
           return rval;
       }}
       return 0;
   }}   
   
    // otherwise do the conversion
    if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS)) {{
        // Just fetch the existing instance
        *sipCppPtr = reinterpret_cast<{CLASS}*>(sipConvertToType(
                sipPy, sipType_{CLASS}, sipTransferObj, SIP_NO_CONVERTORS, 0, sipIsErr));
        return 0;  // not a new instance
    }}
    
    // or create a new instance
    PyObject* o1 = PySequence_ITEM(sipPy, 0);
    PyObject* o2 = PySequence_ITEM(sipPy, 1);
    *sipCppPtr = new {CLASS}(wxPyInt_AsLong(o1), wxPyInt_AsLong(o2));
    Py_DECREF(o1);
    Py_DECREF(o2);
    return SIP_TEMPORARY;
    """.format(**locals())

def convertTwoIntegersTemplate_cffi(klass):
    klass.convertFromPyObject_cffi="""\
    return {PYNAME}(py_obj[0], py_obj[1])
    """
    klass.instanceCheck_cffi="""\
    return (isinstance(py_obj, collections.Sequence) and len(py_obj) >= 2 and
            all([isinstance(py_obj[i], numbers.Number) for i in range(2)]))
    """

def convertFourIntegersTemplate(CLASS):
    # Note: The GIL is already acquired where this code is used.
    return """\
    // is it just a typecheck?
    if (!sipIsErr) {{
        // is it already an instance of {CLASS}?
        if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS))
            return 1;
 
        if (PySequence_Check(sipPy) && PySequence_Size(sipPy) == 4) {{
            int rval = 1;
            PyObject* o1 = PySequence_ITEM(sipPy, 0);
            PyObject* o2 = PySequence_ITEM(sipPy, 1);
            PyObject* o3 = PySequence_ITEM(sipPy, 2);
            PyObject* o4 = PySequence_ITEM(sipPy, 3);
            if (!PyNumber_Check(o1) || !PyNumber_Check(o2) || !PyNumber_Check(o3) || !PyNumber_Check(o4)) 
                rval = 0;
            Py_DECREF(o1);
            Py_DECREF(o2);
            Py_DECREF(o3);
            Py_DECREF(o4);
            return rval;
        }}
        return 0;
    }}   
   
    // otherwise do the conversion
    if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS)) {{
        // Just fetch the existing instance
        *sipCppPtr = reinterpret_cast<{CLASS}*>(sipConvertToType(
                sipPy, sipType_{CLASS}, sipTransferObj, SIP_NO_CONVERTORS, 0, sipIsErr));
        return 0; // not a new instance
    }}
    // or create a new instance
    PyObject* o1 = PySequence_ITEM(sipPy, 0);
    PyObject* o2 = PySequence_ITEM(sipPy, 1);
    PyObject* o3 = PySequence_ITEM(sipPy, 2);
    PyObject* o4 = PySequence_ITEM(sipPy, 3);       
    *sipCppPtr = new {CLASS}(wxPyInt_AsLong(o1), wxPyInt_AsLong(o2),
                             wxPyInt_AsLong(o3), wxPyInt_AsLong(o4));
    Py_DECREF(o1);
    Py_DECREF(o2);
    return SIP_TEMPORARY;
    """.format(**locals())


def convertFourIntegersTemplate_cffi(klass):
    klass.convertFromPyObject_cffi="""\
    return {PYNAME}(py_obj[0], py_obj[1], py_obj[2], py_obj[3])
    """
    klass.instanceCheck_cffi="""\
    return (isinstance(py_obj, collections.Sequence) and len(py_obj) >= 4 and
            all([isinstance(py_obj[i], numbers.Number) for i in range(4)]))
    """


def convertTwoDoublesTemplate(CLASS):
    # Note: The GIL is already acquired where this code is used.
    return """\
    // is it just a typecheck?
    if (!sipIsErr) {{
        // is it already an instance of {CLASS}?
        if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS))
            return 1;
 
        if (PySequence_Check(sipPy) && PySequence_Size(sipPy) == 2) {{
            int rval = 1;
            PyObject* o1 = PySequence_ITEM(sipPy, 0);
            PyObject* o2 = PySequence_ITEM(sipPy, 1);
            if (!PyNumber_Check(o1) || !PyNumber_Check(o2)) 
                rval = 0;
            Py_DECREF(o1);
            Py_DECREF(o2);
            return rval;
        }}
        return 0;
    }}   
   
    // otherwise do the conversion
    if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS)) {{
        // Just fetch the existing instance
        *sipCppPtr = reinterpret_cast<{CLASS}*>(sipConvertToType(
                sipPy, sipType_{CLASS}, sipTransferObj, SIP_NO_CONVERTORS, 0, sipIsErr));
        return 0; // not a new instance
    }}
   
    // or create a new instance
    PyObject* o1 = PySequence_ITEM(sipPy, 0);
    PyObject* o2 = PySequence_ITEM(sipPy, 1);
    *sipCppPtr = new {CLASS}(PyFloat_AsDouble(o1), PyFloat_AsDouble(o2));
    Py_DECREF(o1);
    Py_DECREF(o2);
    return SIP_TEMPORARY;
    """.format(**locals())

def convertTwoDoublesTemplate_cffi(klass):
    klass.convertFromPyObject_cffi="""\
    return {PYNAME}(py_obj[0], py_obj[1])
    """
    klass.instanceCheck_cffi="""\
    return (isinstance(py_obj, collections.Sequence) and len(py_obj) >= 2 and
            all([isinstance(py_obj[i], numbers.Number) for i in range(2)]))
    """


def convertFourDoublesTemplate(CLASS):
    # Note: The GIL is already acquired where this code is used.
    return """\
    // is it just a typecheck?
    if (!sipIsErr) {{
        // is it already an instance of {CLASS}?
        if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS))
            return 1;
 
        if (PySequence_Check(sipPy) && PySequence_Size(sipPy) == 4) {{
            int rval = 1;
            PyObject* o1 = PySequence_ITEM(sipPy, 0);
            PyObject* o2 = PySequence_ITEM(sipPy, 1);
            PyObject* o3 = PySequence_ITEM(sipPy, 2);
            PyObject* o4 = PySequence_ITEM(sipPy, 3);
            if (!PyNumber_Check(o1) || !PyNumber_Check(o2) || !PyNumber_Check(o3) || !PyNumber_Check(o4)) 
                rval = 0;
            Py_DECREF(o1);
            Py_DECREF(o2);
            Py_DECREF(o3);
            Py_DECREF(o4);
            return rval;
        }}
        return 0;
    }}   
    
    // otherwise do the conversion
    if (sipCanConvertToType(sipPy, sipType_{CLASS}, SIP_NO_CONVERTORS)) {{
        // Just fetch the existing instance
        *sipCppPtr = reinterpret_cast<{CLASS}*>(sipConvertToType(
                sipPy, sipType_{CLASS}, sipTransferObj, SIP_NO_CONVERTORS, 0, sipIsErr));
        return 0; // not a new instance
    }}
    
    // or create a new instance
    PyObject* o1 = PySequence_ITEM(sipPy, 0);
    PyObject* o2 = PySequence_ITEM(sipPy, 1);
    PyObject* o3 = PySequence_ITEM(sipPy, 2);
    PyObject* o4 = PySequence_ITEM(sipPy, 3);       
    *sipCppPtr = new {CLASS}(PyFloat_AsDouble(o1), PyFloat_AsDouble(o2),
    PyFloat_AsDouble(o3), PyFloat_AsDouble(o4));
    Py_DECREF(o1);
    Py_DECREF(o2);
    return SIP_TEMPORARY;
    """.format(**locals())

def convertFourDoublesTemplate_cffi(klass):
    klass.convertFromPyObject_cffi="""\
    return {PYNAME}(py_obj[0], py_obj[1], py_obj[2], py_obj[3])
    """
    klass.instanceCheck_cffi="""\
    return (isinstance(py_obj, collections.Sequence) and len(py_obj) >= 4 and
            all([isinstance(py_obj[i], numbers.Number) for i in range(4)]))
    """



#---------------------------------------------------------------------------
# Templates for creating wrappers for type-specific wxList and wxArray classes


def wxListWrapperTemplate(ListClass, ItemClass, module, RealItemClass=None, 
                          includeConvertToType=False, fakeListClassName=None):
    if RealItemClass is None:
        RealItemClass = ItemClass    

    if fakeListClassName:
        TypeDef = "typedef %s %s;" % (ListClass, fakeListClassName)
        ListClass = fakeListClassName
    else:
        TypeDef = ""
        
    moduleName = module.module        
    ItemClass_pyName = removeWxPrefix(ItemClass)
    ListClass_pyName = removeWxPrefix(ListClass)
    
    c = extractors.ClassDef(name='{ListClass}_iterator'.format(**locals()), abstract=True)
    c.addItem(extractors.CppMethodDef(
        ItemClass + '*', '__next__', '()', "return self->__next__();"))

    c.addHeaderCode("""\
        {TypeDef}
        class {ListClass}_iterator {{
        public:
            {ListClass}_iterator({ListClass}::compatibility_iterator start)
                : m_node(start) {{}}
            
            {ItemClass}* __next__() {{
                {RealItemClass}* obj = NULL;
                if (m_node) {{
                    obj = ({RealItemClass}*) m_node->GetData();
                    m_node = m_node->GetNext();
                }}
                else {{
                    PyErr_SetString(PyExc_StopIteration, "");
                }}
                return ({ItemClass}*)obj;
            }}
        private:
            {ListClass}::compatibility_iterator m_node;
        }};""".format(**locals()))
    module.addItem(c)

    c = extractors.ClassDef(name=ListClass)
    c.addHeaderCode(TypeDef)
    c.addItem(extractors.CppMethodDef(
        'Py_ssize_t', '__len__', '()', 'return self->size();'))
    c.addItem(extractors.CppMethodDef(
        ItemClass + '*', '__getitem__', '(size_t index)',
        """\
        if (index < self->size()) {{
            {ListClass}::compatibility_iterator node = self->Item(index);
            if (node) 
                return ({ItemClass}*)node->GetData();
            else
                return NULL;
        }}
        else {{
            wxPyErr_SetString(PyExc_IndexError, "sequence index out of range");
            return NULL;
        }}""".format(**locals())))
      
    c.addItem(extractors.CppMethodDef(
        'int', '__contains__', '(const %s* obj)' % ItemClass,
        """\
        {ListClass}::compatibility_iterator node;
        node = self->Find(({RealItemClass}*)obj);
        return node != NULL;""".format(**locals())))
    c.addItem(extractors.CppMethodDef(
        ListClass + '_iterator*', '__iter__', '()', factory=True,
        body='return new %s_iterator(self->GetFirst());' % ListClass))
    c.addItem(extractors.CppMethodDef(
        'int', '__getitem__', '(%s * obj)' % ItemClass,
        """\
        int idx = self->IndexOf(({RealItemClass}*)obj);
        if (idx == wxNOT_FOUND) {{
            wxPyErr_SetString(PyExc_ValueError,
                              "sequence.index(x): x not in sequence");
        }}
        return idx;""".format(**locals())))
    c.addItem(extractors.CppMethodDef_cffi(
        '_new', isStatic=True,
        pyArgs=extractors.ArgsString('(WL_Object elements)'),
        pyBody="""\
        wrapper_lib.check_args_types(
            ({0}._pyobject_mapping_, elements, "elements"))

        keepalive = []
        ptrs = []
        for item in elements:
            if not isinstance(item, {1}):
                item = {1}._pyobject_mapping_.convert(item)
                keepalive.append(item)
            ptrs.append(wrapper_lib.get_ptr(item))

        ptr = call(len(ptrs), ffi.new('void*[]', ptrs))
        return wrapper_lib.obj_from_ptr(ptr, {0}, True)
        """.format(ListClass_pyName, ItemClass_pyName),
        cReturnType='void *',
        cArgsString='(size_t count, void **elements)',
        # Don't send data to the constructor! This calls virtual methods,
        # which are not yet defined in the base C++ class... wx is broken.
        cBody='''
        {ListClass} *list = new {ListClass}; 
        list->DeleteContents(true); // tell the list to take ownership of the items
        for (Py_ssize_t i = 0; i < count; i++) {{
            list->Append(new {ItemClass}(*({ItemClass}*)elements[i]));
        }}
        return list;
        '''.format(**locals()),
    ))
    # TODO:  add support for index(value, [start, [stop]])
    c.addPyMethod(
        '__repr__', '(self)',
        'return "{ListClass_pyName}: " + repr(list(self))'.format(**locals()))

    if includeConvertToType:
        c.convertFromPyObject = '''\
        // Code to test a PyObject for compatibility
        if (!sipIsErr) {{
            int success = TRUE;
            // is it already a {ListClass}?
            if (sipCanConvertToType(sipPy, sipType_{ListClass}, SIP_NO_CONVERTORS))
                return success;
            // otherwise ensure that it is a sequence
            if (! PySequence_Check(sipPy)) 
                success = FALSE;
            // ensure it is not a string or unicode object (they are sequences too)
            else if (PyBytes_Check(sipPy) || PyUnicode_Check(sipPy))
                success = FALSE;
            // ensure each item can be converted to {ItemClass}
            else {{
                Py_ssize_t i, len = PySequence_Length(sipPy);
                for (i=0; i<len; i++) {{
                    PyObject* item = PySequence_ITEM(sipPy, i);
                    if (!sipCanConvertToType(item, sipType_{ItemClass}, SIP_NOT_NONE)) {{
                        Py_DECREF(item);
                        success = FALSE;
                        break;
                    }}
                    Py_DECREF(item);
                }}    
            }}
            if (!success)            
                PyErr_SetString(PyExc_TypeError, "Sequence of {ItemClass} compatible objects expected.");
            return success;
        }}

        // Is it already a {ListClass}? Return the exiting instance if so
        if (sipCanConvertToType(sipPy, sipType_{ListClass}, SIP_NO_CONVERTORS)) {{
            *sipCppPtr = reinterpret_cast<{ListClass}*>(
                        sipConvertToType(sipPy, sipType_{ListClass}, NULL, 
                                        SIP_NO_CONVERTORS, 0, sipIsErr));
            return 0;
        }}
        
        // Create a new {ListClass} and convert compatible PyObjects from the sequence
        {ListClass} *list = new {ListClass};
        list->DeleteContents(true); // tell the list to take ownership of the items
        Py_ssize_t i, len = PySequence_Length(sipPy);
        for (i=0; i<len; i++) {{
            int state;
            PyObject* pyItem = PySequence_ITEM(sipPy, i);
            {ItemClass}* cItem = reinterpret_cast<{ItemClass}*>(
                                sipConvertToType(pyItem, sipType_{ItemClass}, 
                                NULL, 0, &state, sipIsErr));
            if (!state)  // a temporary was not created for us, make one now
                cItem = new {ItemClass}(*cItem);
            list->Append(cItem);
            Py_DECREF(pyItem);
        }}
        *sipCppPtr = list;
        return SIP_TEMPORARY;
        '''.format(**locals())

    c.instanceCheck_cffi = """\
    if (not isinstance(py_obj, collections.Sequence) or
        isinstance(py_obj, (str, unicode))):
        return False

    if hasattr({0}, '_pyobject_mapping_'):
        type = ({0}, {0}._pyobject_mapping_)
    else:
        type = {0}
    return all(isinstance(i, type) for i in py_obj)
    """.format(ItemClass_pyName)
    c.convertFromPyObject_cffi = "return %s._new(py_obj)" % ListClass_pyName
    module.addItem(c)



def wxArrayWrapperTemplate(ArrayClass, ItemClass, module):
    moduleName = module.module        
    ArrayClass_pyName = removeWxPrefix(ArrayClass)
    
    c = extractors.ClassDef(name=ArrayClass)
    c.addItem(extractors.CppMethodDef(
        'SIP_SSIZE_T', '__len__', '()',
        'return self->GetCount();'))
    c.addItem(extractors.CppMethodDef(
        ItemClass + '*', '__getitem__', '(size_t index)',
        """\
        if(index < self->GetCount())
            return &self->Item(index);
        else
        {
            wxPyErr_SetString(PyExc_IndexError, "sequence index out of range");
            return NULL;
        }"""))
    c.addItem(extractors.CppMethodDef(
        'int', '__contains__', '(const %s& obj)' % ItemClass,
        """\
        return (self->Index(*obj, false) != wxNOT_FOUND);
        """))
    c.addItem(extractors.CppMethodDef(
        'void', 'append', '(const %s& obj)' % ItemClass,
        "self->Add(*obj);"))

    # TODO:  add support for index(value, [start, [stop]])
    c.addItem(extractors.CppMethodDef(
        'int', 'index', '(const %s& obj)' % ItemClass,
        """\
        int idx = self->Index(*obj, false);
        if(idx == wxNOT_FOUND)
        {
            wxPyErr_SetString(PyExc_ValueError,
                              "sequence.index(x): x not in sequence");
            return -1;
        }
        return idx;
        """))
    c.addPyMethod(
        '__repr__', '(self)',
        body='return "%s: " + repr(list(self))' % ArrayClass_pyName)

    module.addItem(c)



# Same as the above, but for use with  WX_DEFINE_ARRAY_PTR
def wxArrayPtrWrapperTemplate(ArrayClass, ItemClass, module):
    moduleName = module.module        
    ArrayClass_pyName = removeWxPrefix(ArrayClass)
    
    # *** TODO: This can probably be done in a way that is not SIP-specfic.
    # Try creating extractor objects from scratch and attach cppMethods to
    # them as needed, etc..
        
    return extractors.WigCode('''\
class {ArrayClass} 
{{
public:
    SIP_SSIZE_T __len__();
    %MethodCode
        sipRes = sipCpp->GetCount();
    %End

    {ItemClass}* __getitem__(size_t index);
    %MethodCode
        if (index < sipCpp->GetCount()) {{
            sipRes = sipCpp->Item(index);
        }}
        else {{
            wxPyErr_SetString(PyExc_IndexError, "sequence index out of range");
            sipError = sipErrorFail;
        }}
    %End

    int __contains__({ItemClass}* obj);
    %MethodCode
        int idx = sipCpp->Index(obj, false);
        sipRes = idx != wxNOT_FOUND;
    %End

    void append({ItemClass}* obj);
    %MethodCode
        sipCpp->Add(obj);
    %End

    // TODO:  add support for index(value, [start, [stop]])
    int index({ItemClass}* obj);
    %MethodCode
        int idx = sipCpp->Index(obj, false);
        if (idx == wxNOT_FOUND) {{
            sipError = sipErrorFail;
            wxPyErr_SetString(PyExc_ValueError,
                              "sequence.index(x): x not in sequence");
            }}
        sipRes = idx;
    %End
}};

%Extract(id=pycode{moduleName})
def _{ArrayClass_pyName}___repr__(self):
    return "{ArrayClass_pyName}: " + repr(list(self))
{ArrayClass_pyName}.__repr__ = _{ArrayClass_pyName}___repr__
del _{ArrayClass_pyName}___repr__
%End
'''.format(**locals()))




def ObjArrayHelperTemplate(objType, sipType, errmsg):
    """
    Generates a helper function that can convert from a Python sequence of
    objects (or items that can be converted to the target type) into a C
    array of values. Copies are made of the items so the object types should
    support implicit or explicit copies and the copy should be cheap.  
    
    This kind of helper is useful for situations where the C/C++ API takes a
    simple pointer and a count, and there is no higher level container object
    (like a wxList or wxArray) being used. If there is an overloaded method
    that uses one of those types then the C array overload should just be
    ignored. But for those cases where the C array is the only option then this
    helper can be used to make the array from a sequence.
    """
    
    cppCode = """\
// Convert a Python sequence of {objType} objects, or items that can be converted 
// to {objType} into a C array of {objType} instances.
static
{objType}* {objType}_array_helper(PyObject* source, size_t *count)
{{
    {objType}* array;
    Py_ssize_t idx, len;
    wxPyThreadBlocker blocker;
    
    // ensure that it is a sequence
    if (! PySequence_Check(source)) 
        goto error0;
    // ensure it is not a string or unicode object (they are sequences too)
    else if (PyBytes_Check(source) || PyUnicode_Check(source))
        goto error0;
    // ensure each item can be converted to {objType}
    else {{
        len = PySequence_Length(source);
        for (idx=0; idx<len; idx++) {{
            PyObject* item = PySequence_ITEM(source, idx);
            if (!sipCanConvertToType(item, {sipType}, SIP_NOT_NONE)) {{
                Py_DECREF(item);
                goto error0;
            }}
            Py_DECREF(item);
        }}
    }}
    
    // The length of the sequence is returned in count.
    *count = len;
    array = new {objType}[*count];
    if (!array) {{
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate temporary array");
        return NULL;
    }}
    for (idx=0; idx<len; idx++) {{
        PyObject* obj = PySequence_ITEM(source, idx);
        int state = 0;
        int err = 0;
        {objType}* item = reinterpret_cast<{objType}*>(
                        sipConvertToType(obj, {sipType}, NULL, 0, &state, &err));
        array[idx] = *item;
        sipReleaseType((void*)item, {sipType}, state); // delete temporary instances
        Py_DECREF(obj);
    }}
    return array;

error0:
    PyErr_SetString(PyExc_TypeError, "{errmsg}");
    return NULL;
}}
""".format(**locals())

    return cppCode


#---------------------------------------------------------------------------
# type helpers

def guessTypeInt(v):
    if isinstance(v, extractors.EnumValueDef):
        return True
    if isinstance(v, extractors.DefineDef) and '"' not in v.value:
        return True
    type = v.type.replace('const', '')
    type = type.replace(' ', '')
    if type in ['int', 'long', 'byte', 'size_t', 'wxCoord', 'wxEventType']:
        return True
    if 'unsigned' in type:
        return True
    return False


def guessTypeFloat(v):
    type = v.type.replace('const', '')
    type = type.replace(' ', '')
    if type in ['float', 'double', 'wxDouble']:
        return True
    return False


def guessTypeStr(v):
    if hasattr(v, 'value') and '"' in v.value:
        return True
    for t in ['wxString', 'wxChar', 'char*', 'char *']:
        if t in v.type:
            return True
    return False

#---------------------------------------------------------------------------
