def run(module):
    c = module.find('wxPoint2DDouble')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(dd)", self->m_x, self->m_y);
        """, 
        briefDoc="""\
        Get() -> (x,y)\n    
        Return the x and y properties as a tuple.""")

    c = module.find('wxRect2DDouble')
    c.addCppMethod('PyObject*', 'Get', '()', """\
        return sipBuildResult(0, "(dddd)", 
                    self->m_x, self->m_y, self->m_width, self->m_height);
        """, 
        briefDoc="""\
        Get() -> (x, y, width, height)\n    
        Return the rectangle's properties as a tuple.""")
    
