import etgtools.tweaker_tools as tools

def run(module):
    c = module.find('wxGraphicsContext')

    c.addCppMethod('PyObject*', 'GetTextExtent', '(const wxString& text)', 
        pyArgsString="(text) -> (width, height)",
        doc="Gets the dimensions of the string using the currently selected font.",
        body="""\
        wxDouble width = 0.0, height = 0.0;
        self->GetTextExtent(*text, &width, &height, NULL, NULL);
        return sipBuildResult(0, "(dd)", width, height);
        """)

    c.addCppCode(tools.ObjArrayHelperTemplate('wxPoint2D', 'sipType_wxPoint2DDouble',
                    "Expected a sequence of length-2 sequences or wx.Point2D objects."))

    c.addCppMethod('void', 'StrokeLineSegments', '(PyObject* beginPoints, PyObject* endPoints)', 
        pyArgsString="(beginPoint2Ds, endPoint2Ds)",
        doc="Stroke disconnected lines from begin to end points.",
        body="""\
        size_t c1, c2, count;
        wxPoint2D* beginP = wxPoint2D_array_helper(beginPoints, &c1);
        wxPoint2D* endP =   wxPoint2D_array_helper(endPoints, &c2);

        if ( beginP != NULL && endP != NULL ) {
            count = wxMin(c1, c2);
            self->StrokeLines(count, beginP, endP);
        }
        delete [] beginP;
        delete [] endP;
        """)

    c.addCppMethod('void', 'DrawLines', '(PyObject* points, wxPolygonFillMode fillStyle = wxODDEVEN_RULE)', 
        pyArgsString="(point2Ds, fillStyle=ODDEVEN_RULE)",
        doc="Draws a polygon.",
        body="""\
        size_t count;
        wxPoint2D* ptsArray = wxPoint2D_array_helper(points, &count);

        if ( ptsArray != NULL ) {
            self->DrawLines(count, ptsArray, fillStyle);
            delete [] ptsArray;
        }
        """)

    c.addCppMethod('void', 'StrokeLines', '(PyObject* points)', 
        pyArgsString="(point2Ds)",
        doc="Stroke lines conencting all the points.",
        body="""\
        size_t count;
        wxPoint2D* ptsArray = wxPoint2D_array_helper(points, &count);

        if ( ptsArray != NULL ) {
            self->StrokeLines(count, ptsArray);
            delete [] ptsArray;
        }
        """)
