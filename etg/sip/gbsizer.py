def run(module):
    c = module.find('wxGBPosition')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(ii)", self->GetRow(), self->GetCol());
        """, 
        pyArgsString="() -> (row, col)",
        briefDoc="Return the row and col properties as a tuple.")

    c = module.find('wxGBSpan')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(ii)", self->GetRowspan(), self->GetColspan());
        """, 
        pyArgsString="() -> (rowspan, colspan)",
        briefDoc="Return the rowspan and colspan properties as a tuple.")
