def run(module):
    # This file contains implementations of functions for quickly drawing
    # lists of items on the DC. They are called from the CppMethods defined
    # below, which in turn are called from the PyMethods below that.
    c.includeCppCode('src/dc_ex.cpp')
    
    c.addCppMethod('PyObject*', '_DrawPointList', '(PyObject* pyCoords, PyObject* pyPens, PyObject* pyBrushes)',
        body="return wxPyDrawXXXList(*self, wxPyDrawXXXPoint, pyCoords, pyPens, pyBrushes);")

    c.addCppMethod('PyObject*', '_DrawLineList', '(PyObject* pyCoords, PyObject* pyPens, PyObject* pyBrushes)',
        body="return wxPyDrawXXXList(*self, wxPyDrawXXXLine, pyCoords, pyPens, pyBrushes);")

    c.addCppMethod('PyObject*', '_DrawRectangleList', '(PyObject* pyCoords, PyObject* pyPens, PyObject* pyBrushes)',
        body="return wxPyDrawXXXList(*self, wxPyDrawXXXRectangle, pyCoords, pyPens, pyBrushes);")

    c.addCppMethod('PyObject*', '_DrawEllipseList', '(PyObject* pyCoords, PyObject* pyPens, PyObject* pyBrushes)',
        body="return wxPyDrawXXXList(*self, wxPyDrawXXXEllipse, pyCoords, pyPens, pyBrushes);")

    c.addCppMethod('PyObject*', '_DrawPolygonList', '(PyObject* pyCoords, PyObject* pyPens, PyObject* pyBrushes)',
        body="return wxPyDrawXXXList(*self, wxPyDrawXXXPolygon, pyCoords, pyPens, pyBrushes);")

    c.addCppMethod('PyObject*', '_DrawTextList', 
        '(PyObject* textList, PyObject* pyPoints, PyObject* foregroundList, PyObject* backgroundList)',
        body="return wxPyDrawTextList(*self, textList, pyPoints, foregroundList, backgroundList);")

    
    c.addPyMethod('DrawPointList', '(self, points, pens=None)',
        doc="""\
            Draw a list of points as quickly as possible.
    
            :param points: A sequence of 2-element sequences representing 
                           each point to draw, (x,y).
            :param pens:   If None, then the current pen is used.  If a single 
                           pen then it will be used for all points.  If a list of 
                           pens then there should be one for each point in points.
            """,
        body="""\
            if pens is None:
                pens = []
            elif isinstance(pens, wx.Pen):
                pens = [pens]
            elif len(pens) != len(points):
                raise ValueError('points and pens must have same length')
            return self._DrawPointList(points, pens, [])
            """)
