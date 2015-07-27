#---------------------------------------------------------------------------
# Name:        etg/_core.py
# Author:      Robin Dunn
#
# Created:     8-Nov-2010
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools
from etgtools import PyFunctionDef, PyCodeDef, PyPropertyDef

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "_core"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script.
ITEMS  = [ ]




# The list of other ETG scripts and back-end generator modules that are
# included as part of this module. These items are in their own etg scripts
# for easier maintainability, but their class and function definitions are
# intended to be part of this module, not their own module. This also makes it
# easier to promote one of these to module status later if desired, simply
# remove it from this list of Includes, and change the MODULE value in the
# promoted script to be the same as its NAME.

INCLUDES = [  # base and core stuff
              'defs',
              #'debug',
              'object',
              'wxpy_api',
              'arrayholder',
              'wxstring',
              'filename',
              'arrays',
              'clntdata',
              'clntdatactnr',
              'userdata',
              'wxpybuffer',

              'stockgdi',
              'longlong',
              'wxdatetime',
              #'stopwatch',

              'windowid',
              'platinfo',
              'vidmode',
              #'display',
              'intl',
              'translation',

              'cmndata',
              'gdicmn',
              'geometry',
              'affinematrix2d',
              #'position',
              'colour',

              'stream', 'filesys',

              # GDI and graphics
              'image',
              'gdiobj',
              'bitmap',
              'icon', 'iconloc', 'iconbndl',
              'font',
              'fontutil',
              'pen',
              'brush',
              'cursor',
              'region',
              'dc',
              'dcclient',
              'dcmemory',
              #'dcbuffer',
              #'dcscreen',
              #'dcgraph',
              #'dcmirror',
              'dcprint',
              #'dcps',
              #'dcsvg',
              'graphics',
              'imaglist',
              #'overlay',
              #'renderer',
              #'rawbmp',

              # more core
              'accel',
              'log',
              'dataobj',
              'dnd',
              'clipbrd',
              'config',
              #'variant',
              'tracker',
              'kbdstate',
              'mousestate',
              'tooltip',
              'layout',
              'event',
              'pyevent',
              'sizer', 'gbsizer', 'wrapsizer',
              'stdpaths',

              'eventfilter',
              'evtloop',
              'apptrait',
              'app',

              # basic windows and stuff
              'timer',
              'window',
              'validate',
              'panel',
              'menuitem',
              'menu',
              'scrolwin',
              #'vscroll',

              # controls
              'control',
              'ctrlsub',
              'statbmp',
              'stattext',
              'statbox',
              'statusbar',
              #'choice',
              'anybutton',
              'button',
              'bmpbuttn',
              'withimage',
              'bookctrl',
              'notebook',
              'splitter',
              #'collpane',
              #'statline',
              'textcompleter',
              'textentry',
              'textctrl',
              'combobox',
              'checkbox',
              #'listbox',
              #'checklst',
              #'gauge',
              'headercol',
              'headerctrl',
              'srchctrl',
              #'radiobox',
              #'radiobut',
              #'slider',
              #'spinbutt',
              'spinctrl',
              #'tglbtn',
              #'scrolbar',
              'toolbar',
              #'infobar',
              'listctrl',
              #'treeitemdata',
              'treectrl',
              #'pickers',
              #'filectrl',
              'combo',
              #'choicebk',
              #'listbook',
              #'toolbook',
              #'treebook',
              #'vlbox',

              # toplevel and dialogs
              'nonownedwnd',
              'toplevel',
              'dialog',
              #'dirdlg',
              #'dirctrl',
              #'filedlg',
              'frame',
              #'msgdlg',
              #'richmsgdlg',
              #'progdlg',
              #'popupwin',
              #'tipwin',
              #'colordlg',
              #'choicdlg',
              #'fdrepdlg',
              #'mdi',
              #'fontdlg',
              #'rearrangectrl',
              'minifram',
              #'textdlg',

              # misc
              'power',
              'utils',
              'process',
              #'uiaction',
              #'snglinst',
              #'help',
              #'cshelp',
              #'settings',
              'sysopt',
              #'artprov',
              'dragimag',
              #'printfw',
              #'printdlg',
              #'mimetype',
              #'busyinfo',
              'caret',
              #'fontenum',
              #'fontmap',
              #'mousemanager',
              #'filehistory',
              #'cmdproc',
              #'fswatcher',
              #'preferences',
              #'modalhook',
              ]


# Separate the list into those that are generated from ETG scripts and the
# rest. These lists can be used from the build scripts to get a list of
# sources and/or additional dependencies when building this extension module.
ETGFILES = ['etg/%s.py' % NAME] + tools.getEtgFiles(INCLUDES)
DEPENDS = tools.getNonEtgFiles(INCLUDES)
OTHERDEPS = [ 'src/core_ex.py',
              'src/core_ex.cpp',
              'src/cffi/core_ex.cpp',
              'etg/sip/_core.py',
              'etg/cffi/_core.py',
            ]


#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    module.check4unittest = False

    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.


    module.addInclude(INCLUDES)
    module.includePyCode('src/core_ex.py', order=10)

    module.addHeaderCode("""\
    #if defined(__GNUC__)
        #pragma GCC diagnostic ignored "-Wdeprecated-declarations"
    #endif
    """)

    module.addPyFunction('version', '()',
        doc="""Returns a string containing version and port info""",
        body="""\
            if wx.Port == '__WXMSW__':
                port = 'msw'
            elif wx.Port == '__WXMAC__':
                if 'wxOSX-carbon' in wx.PlatformInfo:
                    port = 'osx-carbon'
                else:
                    port = 'osx-cocoa'
            elif wx.Port == '__WXGTK__':
                port = 'gtk'
                if 'gtk2' in wx.PlatformInfo:
                    port = 'gtk2'
            else:
                port = '???'
            return "%s %s (phoenix)" % (wx.VERSION_STRING, port)
            """)


    module.addPyFunction('CallAfter', '(callableObj, *args, **kw)', doc="""\
            Call the specified function after the current and pending event
            handlers have been completed.  This is also good for making GUI
            method calls from non-GUI threads.  Any extra positional or
            keyword args are passed on to the callable when it is called.

            :param PyObject callableObj: the callable object
            :param args: arguments to be passed to the callable object
            :param kw: keywords to be passed to the callable object

            .. seealso::
                :class:`CallLater`

            """,
        body="""\
            assert callable(callableObj), "callableObj is not callable"
            app = wx.GetApp()
            assert app is not None, 'No wx.App created yet'

            if not hasattr(app, "_CallAfterId"):
                app._CallAfterId = wx.NewEventType()
                app.Connect(-1, -1, app._CallAfterId,
                            lambda event: event.callable(*event.args, **event.kw) )
            evt = wx.PyEvent()
            evt.SetEventType(app._CallAfterId)
            evt.callable = callableObj
            evt.args = args
            evt.kw = kw
            wx.PostEvent(app, evt)""")


    module.addPyClass('CallLater', ['object'],
        doc="""\
            A convenience class for :class:`Timer`, that calls the given callable
            object once after the given amount of milliseconds, passing any
            positional or keyword args.  The return value of the callable is
            availbale after it has been run with the :meth:`~CallLater.GetResult` method.

            If you don't need to get the return value or restart the timer
            then there is no need to hold a reference to this object.  It will
            hold a reference to itself while the timer is running (the timer
            has a reference to :meth:`~CallLater.Notify`) but the cycle will be broken when
            the timer completes, automatically cleaning up the :class:`CallLater`
            object.

            .. seealso::
                :func:`CallAfter`

            """,
        items = [
            PyFunctionDef('__init__', '(self, millis, callableObj, *args, **kwargs)',
                doc="""\
                    A convenience class for :class:`Timer`, that calls the given callable
                    object once after the given amount of milliseconds, passing any
                    positional or keyword args.  The return value of the callable is
                    availbale after it has been run with the :meth:`~CallLater.GetResult` method.

                    :param int millis: number of milli seconds
                    :param PyObject callableObj: the callable object
                    :param args: arguments to be passed to the callable object
                    :param kw: keywords to be passed to the callable object
                """,

                body="""\
                    assert callable(callableObj), "callableObj is not callable"
                    self.millis = millis
                    self.callable = callableObj
                    self.SetArgs(*args, **kwargs)
                    self.runCount = 0
                    self.running = False
                    self.hasRun = False
                    self.result = None
                    self.timer = None
                    self.Start()"""),

            PyFunctionDef('__del__', '(self)', 'self.Stop()'),

            PyFunctionDef('Start', '(self, millis=None, *args, **kwargs)',
                doc="""\
                    (Re)start the timer

                    :param int millis: number of milli seconds
                    :param args: arguments to be passed to the callable object
                    :param kw: keywords to be passed to the callable object

                    """,
                body="""\
                    self.hasRun = False
                    if millis is not None:
                        self.millis = millis
                    if args or kwargs:
                        self.SetArgs(*args, **kwargs)
                    self.Stop()
                    self.timer = wx.PyTimer(self.Notify)
                    self.timer.Start(self.millis, wx.TIMER_ONE_SHOT)
                    self.running = True"""),
            PyCodeDef('Restart = Start'),

            PyFunctionDef('Stop', '(self)',
                doc="Stop and destroy the timer.",
                body="""\
                    if self.timer is not None:
                        self.timer.Stop()
                        self.timer = None"""),

            PyFunctionDef('GetInterval', '(self)', """\
                if self.timer is not None:
                    return self.timer.GetInterval()
                else:
                    return 0"""),

            PyFunctionDef('IsRunning', '(self)',
                """return self.timer is not None and self.timer.IsRunning()"""),

            PyFunctionDef('SetArgs', '(self, *args, **kwargs)',
                doc="""\
                    (Re)set the args passed to the callable object.  This is
                    useful in conjunction with :meth:`Restart` if you want to schedule a
                    new call to the same callable object but with different
                    parameters.

                    :param args: arguments to be passed to the callable object
                    :param kw: keywords to be passed to the callable object

                    """,
                body="""\
                    self.args = args
                    self.kwargs = kwargs"""),

            PyFunctionDef('HasRun', '(self)', 'return self.hasRun',
                doc="""\
                    Returns whether or not the callable has run.

                    :rtype: bool

                    """),

            PyFunctionDef('GetResult', '(self)', 'return self.result',
                doc="""\
                    Returns the value of the callable.

                    :rtype: a Python object
                    :return: result from callable
                    """),

            PyFunctionDef('Notify', '(self)',
                doc="The timer has expired so call the callable.",
                body="""\
                    if self.callable and getattr(self.callable, 'im_self', True):
                        self.runCount += 1
                        self.running = False
                        self.result = self.callable(*self.args, **self.kwargs)
                    self.hasRun = True
                    if not self.running:
                        # if it wasn't restarted, then cleanup
                        wx.CallAfter(self.Stop)"""),

            PyPropertyDef('Interval', 'GetInterval'),
            PyPropertyDef('Result', 'GetResult'),
            ])

    module.addPyCode("FutureCall = deprecated(CallLater, 'Use CallLater instead.')")

    module.addPyCode("""\
        def GetDefaultPyEncoding():
            return "utf-8"
        GetDefaultPyEncoding = deprecated(GetDefaultPyEncoding, msg="wxPython now always uses utf-8")
        """)

    module.addCppFunction('bool', 'IsMainThread', '()',
        doc="Returns ``True`` if the current thread is what wx considers the GUI thread.",
        body="return wxThread::IsMain();")


    tools.runGeneratorSpecificScript(module)

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)



#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
