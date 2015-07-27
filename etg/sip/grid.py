import etgtools

def run(module):
    def fixEditorClass(name):
        klass = module.find(name)
        assert isinstance(klass, etgtools.ClassDef)

        klass.addCppMethod('PyObject*', 'EndEdit', '(int row, int col, const wxGrid* grid, const wxString& oldval)',
            cppSignature='bool (int row, int col, const wxGrid* grid, const wxString& oldval, wxString* newval)',
            pyArgsString='(row, col, grid, oldval)',
            isVirtual=True, 
            isPureVirtual=pureVirtual,
            doc="""\
                End editing the cell.
                
                This function must check if the current value of the editing cell
                is valid and different from the original value in its string
                form. If not then simply return None.  If it has changed then 
                this method should save the new value so that ApplyEdit can
                apply it later and the string representation of the new value 
                should be returned.
                
                Notice that this method shoiuld not modify the grid as the 
                change could still be vetoed.                
                """,
            
            # Code for Python --> C++ calls.  Make it return newval or None.
            body="""\
                bool rv;
                wxString newval;
                rv = self->EndEdit(row, col, grid, *oldval, &newval);
                if (rv) {
                    return wx2PyString(newval);
                }
                else {
                    Py_INCREF(Py_None);
                    return Py_None;
                }
                """,
    
            # Code for C++ --> Python calls. This is used when a C++ method
            # call needs to be reflected to a call to the overridden Python
            # method, so we need to translate between the real C++ siganture
            # and the Python signature.
            virtualCatcherCode="""\
                // VirtualCatcherCode for wx.grid.GridCellEditor.EndEdit
                PyObject *result;
                result = sipCallMethod(0, sipMethod, "iiDN", row, col,
                                       const_cast<wxGrid *>(grid),sipType_wxGrid,NULL);
                if (result == Py_None) {
                    sipRes = false;
                } 
                else {
                    sipRes = true;
                    *newval = Py2wxString(result);
                }
                Py_DECREF(result);
                """  if pureVirtual else "",  # only used with the base class
            )

    for name in ITEMS:
        if 'Cell' in name and 'Editor' in name:
            fixEditorClass(name)            
    
    c = module.find('wxGridCellCoords')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(ii)", self->GetRow(), self->GetCol());
        """, 
        pyArgsString="() -> (row,col)",
        briefDoc="Return the row and col properties as a tuple.")

