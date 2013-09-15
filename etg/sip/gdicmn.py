def run(module):
    c = module.findItem('wxPoint')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(ii)", self->x, self->y);
        """, 
        pyArgsString="() -> (x,y)",
        briefDoc="Return the x and y properties as a tuple.")

    c = module.findItem('wxSize')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(ii)", self->GetWidth(), self->GetHeight());
        """,
        pyArgsString="() -> (width, height)",
        briefDoc="Return the width and height properties as a tuple.")

    c = module.findItem('wxRect')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(iiii)", 
                              self->x, self->y, self->width, self->height);
        """, 
        pyArgsString="() -> (x, y, width, height)",
        briefDoc="Return the rectangle's properties as a tuple.")

    c = module.findItem('wxRealPoint')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(dd)", self->x, self->y);
        """, 
        pyArgsString="() -> (x, y)",
        briefDoc="Return the point's properties as a tuple.")
    
