#---------------------------------------------------------------------------
# Name:        etg/treectrl.py
# Author:      Robin Dunn
#
# Created:     26-Mar-2012
# Copyright:   (c) 2013 by Total Control Software
# License:     wxWindows License
#---------------------------------------------------------------------------

import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"   
MODULE    = "_core"
NAME      = "treectrl"   # Base name of the file to generate to for this script
DOCSTRING = ""

# The classes and/or the basename of the Doxygen XML files to be processed by
# this script. 
ITEMS  = [ "wxTreeItemId",
           ##"wxTreeItemData",  We're using a MappedType instead
           "wxTreeCtrl",
           "wxTreeEvent",           
           ]    

#---------------------------------------------------------------------------

def run():
    # Parse the XML file(s) building a collection of Extractor objects
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)
    etgtools.parseDoxyXML(module, ITEMS)
    
    #-----------------------------------------------------------------
    # Tweak the parsed meta objects in the module object as needed for
    # customizing the generated code and docstrings.
    
    
    #-------------------------------------------------------
    c = module.find('wxTreeItemId')
    assert isinstance(c, etgtools.ClassDef)
    c.addCppMethod('int', '__nonzero__', '()', """\
        return self->IsOk();
        """)

    td = etgtools.TypedefDef(name='wxTreeItemIdValue', type='void*')
    module.insertItemBefore(c, td)

    #-------------------------------------------------------
    module.addPyCode("""\
        def TreeItemData(data):
            return data
        TreeItemData = deprecated(TreeItemData, "The TreeItemData class no longer exists, just pass your object directly to the tree instead.")
        """)
    
    #-------------------------------------------------------
    c = module.find('wxTreeCtrl')
    tools.fixWindowClass(c)
    module.addGlobalStr('wxTreeCtrlNameStr', before=c)
    
    
    # Set all wxTreeItemData parameters to transfer ownership.  Is this still needed with MappedTypes?
    for item in c.allItems():
        if hasattr(item, 'type') and item.type == 'wxTreeItemData *' and \
           isinstance(item, etgtools.ParamDef):
                item.transfer = True

    c.addPyCode("""\
        TreeCtrl.GetItemPyData = wx.deprecated(TreeCtrl.GetItemData, 'Use GetItemData instead.')
        TreeCtrl.SetItemPyData = wx.deprecated(TreeCtrl.SetItemData, 'Use SetItemData instead.')
        TreeCtrl.GetPyData = wx.deprecated(TreeCtrl.GetItemData, 'Use GetItemData instead.')
        TreeCtrl.SetPyData = wx.deprecated(TreeCtrl.SetItemData, 'Use SetItemData instead.')
        """)

    
    # We can't use wxClassInfo
    c.find('EditLabel.textCtrlClass').ignore()

    # TODO(amauryfa): GetSelections
    # TODO(amauryfa): GetBoundingRect
    
    # switch the virtualness back on for those methods that need to have it.
    c.find('OnCompareItems').isVirtual = True
    
    
    # transfer imagelist ownership
    c.find('AssignImageList.imageList').transfer = True
    c.find('AssignStateImageList.imageList').transfer = True
    c.find('AssignButtonsImageList.imageList').transfer = True
    
    
    # Make the cookie values be returned, instead of setting it through the parameter
    c.find('GetFirstChild.cookie').out = True
    c.find('GetNextChild.cookie').inOut = True


    # TODO: These don't exist on MSW, Are they important enough that we
    # should provide them for the other platforms anyway?
    c.find('AssignButtonsImageList').ignore()
    c.find('GetButtonsImageList').ignore()
    c.find('SetButtonsImageList').ignore()

    
    #-------------------------------------------------------
    c = module.find('wxTreeEvent')
    tools.fixEventClass(c)
    
    c.addPyCode("""\
        EVT_TREE_BEGIN_DRAG        = PyEventBinder(wxEVT_TREE_BEGIN_DRAG       , 1)
        EVT_TREE_BEGIN_RDRAG       = PyEventBinder(wxEVT_TREE_BEGIN_RDRAG      , 1)
        EVT_TREE_BEGIN_LABEL_EDIT  = PyEventBinder(wxEVT_TREE_BEGIN_LABEL_EDIT , 1)
        EVT_TREE_END_LABEL_EDIT    = PyEventBinder(wxEVT_TREE_END_LABEL_EDIT   , 1)
        EVT_TREE_DELETE_ITEM       = PyEventBinder(wxEVT_TREE_DELETE_ITEM      , 1)
        EVT_TREE_GET_INFO          = PyEventBinder(wxEVT_TREE_GET_INFO         , 1)
        EVT_TREE_SET_INFO          = PyEventBinder(wxEVT_TREE_SET_INFO         , 1)
        EVT_TREE_ITEM_EXPANDED     = PyEventBinder(wxEVT_TREE_ITEM_EXPANDED    , 1)
        EVT_TREE_ITEM_EXPANDING    = PyEventBinder(wxEVT_TREE_ITEM_EXPANDING   , 1)
        EVT_TREE_ITEM_COLLAPSED    = PyEventBinder(wxEVT_TREE_ITEM_COLLAPSED   , 1)
        EVT_TREE_ITEM_COLLAPSING   = PyEventBinder(wxEVT_TREE_ITEM_COLLAPSING  , 1)
        EVT_TREE_SEL_CHANGED       = PyEventBinder(wxEVT_TREE_SEL_CHANGED      , 1)
        EVT_TREE_SEL_CHANGING      = PyEventBinder(wxEVT_TREE_SEL_CHANGING     , 1)
        EVT_TREE_KEY_DOWN          = PyEventBinder(wxEVT_TREE_KEY_DOWN         , 1)
        EVT_TREE_ITEM_ACTIVATED    = PyEventBinder(wxEVT_TREE_ITEM_ACTIVATED   , 1)
        EVT_TREE_ITEM_RIGHT_CLICK  = PyEventBinder(wxEVT_TREE_ITEM_RIGHT_CLICK , 1)
        EVT_TREE_ITEM_MIDDLE_CLICK = PyEventBinder(wxEVT_TREE_ITEM_MIDDLE_CLICK, 1)
        EVT_TREE_END_DRAG          = PyEventBinder(wxEVT_TREE_END_DRAG         , 1)
        EVT_TREE_STATE_IMAGE_CLICK = PyEventBinder(wxEVT_TREE_STATE_IMAGE_CLICK, 1)
        EVT_TREE_ITEM_GETTOOLTIP   = PyEventBinder(wxEVT_TREE_ITEM_GETTOOLTIP,   1)
        EVT_TREE_ITEM_MENU         = PyEventBinder(wxEVT_TREE_ITEM_MENU,         1)
        
        # deprecated wxEVT aliases
        wxEVT_COMMAND_TREE_BEGIN_DRAG         = wxEVT_TREE_BEGIN_DRAG
        wxEVT_COMMAND_TREE_BEGIN_RDRAG        = wxEVT_TREE_BEGIN_RDRAG
        wxEVT_COMMAND_TREE_BEGIN_LABEL_EDIT   = wxEVT_TREE_BEGIN_LABEL_EDIT
        wxEVT_COMMAND_TREE_END_LABEL_EDIT     = wxEVT_TREE_END_LABEL_EDIT
        wxEVT_COMMAND_TREE_DELETE_ITEM        = wxEVT_TREE_DELETE_ITEM
        wxEVT_COMMAND_TREE_GET_INFO           = wxEVT_TREE_GET_INFO
        wxEVT_COMMAND_TREE_SET_INFO           = wxEVT_TREE_SET_INFO
        wxEVT_COMMAND_TREE_ITEM_EXPANDED      = wxEVT_TREE_ITEM_EXPANDED
        wxEVT_COMMAND_TREE_ITEM_EXPANDING     = wxEVT_TREE_ITEM_EXPANDING
        wxEVT_COMMAND_TREE_ITEM_COLLAPSED     = wxEVT_TREE_ITEM_COLLAPSED
        wxEVT_COMMAND_TREE_ITEM_COLLAPSING    = wxEVT_TREE_ITEM_COLLAPSING
        wxEVT_COMMAND_TREE_SEL_CHANGED        = wxEVT_TREE_SEL_CHANGED
        wxEVT_COMMAND_TREE_SEL_CHANGING       = wxEVT_TREE_SEL_CHANGING
        wxEVT_COMMAND_TREE_KEY_DOWN           = wxEVT_TREE_KEY_DOWN
        wxEVT_COMMAND_TREE_ITEM_ACTIVATED     = wxEVT_TREE_ITEM_ACTIVATED
        wxEVT_COMMAND_TREE_ITEM_RIGHT_CLICK   = wxEVT_TREE_ITEM_RIGHT_CLICK
        wxEVT_COMMAND_TREE_ITEM_MIDDLE_CLICK  = wxEVT_TREE_ITEM_MIDDLE_CLICK
        wxEVT_COMMAND_TREE_END_DRAG           = wxEVT_TREE_END_DRAG
        wxEVT_COMMAND_TREE_STATE_IMAGE_CLICK  = wxEVT_TREE_STATE_IMAGE_CLICK
        wxEVT_COMMAND_TREE_ITEM_GETTOOLTIP    = wxEVT_TREE_ITEM_GETTOOLTIP
        wxEVT_COMMAND_TREE_ITEM_MENU          = wxEVT_TREE_ITEM_MENU        
        """)
    
    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)
    
    
#---------------------------------------------------------------------------
if __name__ == '__main__':
    run()

