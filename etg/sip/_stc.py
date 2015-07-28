import etgtools

def run(module):
    c = module.find('wxStyledTextCtrl')

    # Replace the *Pointer methods with ones that return a memoryview object instead.
    c.find('GetCharacterPointer').ignore()
    c.addCppMethod('PyObject*', 'GetCharacterPointer', '()',
        doc="""\
            Compact the document buffer and return a read-only memoryview 
            object of the characters in the document.""",
        body="""
            const char* ptr = self->GetCharacterPointer();
            Py_ssize_t len = self->GetLength();
            PyObject* rv;
            wxPyBLOCK_THREADS( rv = wxPyMakeBuffer((void*)ptr, len, true) );
            return rv;
            """)
    
    c.find('GetRangePointer').ignore()
    c.addCppMethod('PyObject*', 'GetRangePointer', '(int position, int rangeLength)',
        doc="""\
            Return a read-only pointer to a range of characters in the 
            document. May move the gap so that the range is contiguous, 
            but will only move up to rangeLength bytes.""",
        body="""
            const char* ptr = self->GetRangePointer(position, rangeLength);
            Py_ssize_t len = rangeLength;
            PyObject* rv;
            wxPyBLOCK_THREADS( rv = wxPyMakeBuffer((void*)ptr, len, true) );
            return rv;
            """)

