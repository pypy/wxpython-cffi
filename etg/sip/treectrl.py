import etgtools

def run(module):
    c = module.find('wxTreeCtrl')
    # Replace GetSelections with a method that returns a Python list
    # size_t GetSelections(wxArrayTreeItemIds& selection) const;
    c.find('GetSelections').ignore()
    c.addCppMethod('PyObject*', 'GetSelections', '()',
        doc='Returns a list of currently selected items in the tree.  This function '
            'can be called only if the control has the wx.TR_MULTIPLE style.',
        body="""\
        wxPyThreadBlocker blocker;
        PyObject*           rval = PyList_New(0);
        wxArrayTreeItemIds  array;
        size_t              num, x;
        num = self->GetSelections(array);
        for (x=0; x < num; x++) {
            wxTreeItemId *tii = new wxTreeItemId(array.Item(x));
            PyObject* item = wxPyConstructObject((void*)tii, wxT("wxTreeItemId"), true);
            PyList_Append(rval, item);
            Py_DECREF(item);
        }
        return rval;
        """)
    
    # Change GetBoundingRect to return the rectangle instead of modifying the parameter.
    #bool GetBoundingRect(const wxTreeItemId& item, wxRect& rect, bool textOnly = false) const;    
    c.find('GetBoundingRect').ignore()
    c.addCppMethod('PyObject*', 'GetBoundingRect', '(const wxTreeItemId& item, bool textOnly=false)',
        doc="""\
        Returns the rectangle bounding the item. If textOnly is true,
        only the rectangle around the item's label will be returned, otherwise
        the item's image is also taken into account. The return value may be None 
        if the rectangle was not successfully retrieved, such as if the item is 
        currently not visible.
        """,
        isFactory=True,
        body="""\
        wxRect rect;
        if (self->GetBoundingRect(*item, rect, textOnly)) {
            wxPyThreadBlocker blocker;
            wxRect* r = new wxRect(rect);
            PyObject* val = wxPyConstructObject((void*)r, wxT("wxRect"), true);
            return val;
        }
        else
            RETURN_NONE();
        """)
    
    
