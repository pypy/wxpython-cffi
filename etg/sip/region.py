def run(module):
    c = module.find('wxRegion')

    # Replace one of the constructors with one having a more python-friendly API
    c.find('wxRegion').findOverload('points').ignore()
    c.addCppCode(tools.ObjArrayHelperTemplate('wxPoint', 'sipType_wxPoint',
                    "Expected a sequence of length-2 sequences or wx.Point objects."))
    c.addCppCtor_sip('(PyObject* points, wxPolygonFillMode fillStyle = wxODDEVEN_RULE)',
        doc="""\
        Constructs a region corresponding to the polygon made from the points
        in the provided sequence.""",
        body="""\
        size_t count;
        wxPoint* array = wxPoint_array_helper(points, &count);
        if ( array != NULL ) {
            sipCpp = new wxRegion(count, array, fillStyle);
            delete [] array;
        }
        if (PyErr_Occurred()) sipIsErr = 1;
        """)
