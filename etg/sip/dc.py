def run(module):
    c = module.find('wxDC')

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
