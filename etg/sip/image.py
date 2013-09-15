def run(module):
    c = module.find('wxImage')

    c.addCppCtor_sip('(int width, int height, wxPyBuffer* data)',
        doc="Creates an image from RGB data in memory.",
        body="""\
            if (! data->checkSize(width*height*3)) 
                return NULL;
            void* copy = data->copy();
            if (! copy) 
                return NULL;
            sipCpp = new sipwxImage;
            sipCpp->Create(width, height, (byte*)copy);            
            """)
      
    c.addCppCtor_sip('(int width, int height, wxPyBuffer* data, wxPyBuffer* alpha)',
        doc="Creates an image from RGB data in memory, plus an alpha channel",
        body="""\
            void* dcopy; void* acopy;
            if (!data->checkSize(width*height*3) || !alpha->checkSize(width*height))
                return NULL;
            if ((dcopy = data->copy()) == NULL || (acopy = alpha->copy()) == NULL)
                return NULL;
            sipCpp = new sipwxImage;
            sipCpp->Create(width, height, (byte*)dcopy, (byte*)acopy, false);
            """)
      
    c.addCppCtor_sip('(const wxSize& size, wxPyBuffer* data)',
        doc="Creates an image from RGB data in memory.",
        body="""\
            if (! data->checkSize(size->x*size->y*3)) 
                return NULL;
            void* copy = data->copy();
            if (! copy) 
                return NULL;
            sipCpp = new sipwxImage;
            sipCpp->Create(size->x, size->y, (byte*)copy, false);
            """)
      
    c.addCppCtor_sip('(const wxSize& size, wxPyBuffer* data, wxPyBuffer* alpha)',
        doc="Creates an image from RGB data in memory, plus an alpha channel",
        body="""\
            void* dcopy; void* acopy;
            if (!data->checkSize(size->x*size->y*3) || !alpha->checkSize(size->x*size->y))
                return NULL;
            if ((dcopy = data->copy()) == NULL || (acopy = alpha->copy()) == NULL)
                return NULL;
            sipCpp = new sipwxImage;
            sipCpp->Create(size->x, size->y, (byte*)dcopy, (byte*)acopy, false);
            """)


    # GetData() and GetAlpha() return a copy of the image data/alpha bytes as
    # a bytearray object. 
    c.find('GetData').ignore()
    c.find('GetAlpha').findOverload('()').ignore()
    c.addCppMethod('PyObject*', 'GetData', '()',
        doc="Returns a copy of the RGB bytes of the image.",
        body="""\
            byte* data = self->GetData();
            Py_ssize_t len = self->GetWidth() * self->GetHeight() * 3;
            PyObject* rv = NULL;
            wxPyBLOCK_THREADS( rv = PyByteArray_FromStringAndSize((const char*)data, len));
            return rv;           
            """)
    
    c.addCppMethod('PyObject*', 'GetAlpha', '()',
        doc="Returns a copy of the Alpha bytes of the image.",
        body="""\
            byte* data = self->GetAlpha();
            Py_ssize_t len = self->GetWidth() * self->GetHeight();
            PyObject* rv = NULL;
            wxPyBLOCK_THREADS( rv = PyByteArray_FromStringAndSize((const char*)data, len));
            return rv;           
            """)

    # GetDataBuffer, GetAlphaBuffer provide direct access to the image's
    # internal buffers as a writable buffer object.  We'll use memoryview 
    # objects.
    c.addCppMethod('PyObject*', 'GetDataBuffer', '()',
        doc="""\
        Returns a writable Python buffer object that is pointing at the RGB
        image data buffer inside the :class:`Image`. You need to ensure that you do
        not use this buffer object after the image has been destroyed.""",
        body="""\
            byte* data = self->GetData();
            Py_ssize_t len = self->GetWidth() * self->GetHeight() * 3;
            PyObject* rv;
            wxPyThreadBlocker blocker;
            rv = wxPyMakeBuffer(data, len);
            return rv;
            """)

    c.addCppMethod('PyObject*', 'GetAlphaBuffer', '()',
        doc="""\
        Returns a writable Python buffer object that is pointing at the Alpha
        data buffer inside the :class:`Image`. You need to ensure that you do
        not use this buffer object after the image has been destroyed.""",
        body="""\
            byte* data = self->GetAlpha();
            Py_ssize_t len = self->GetWidth() * self->GetHeight();
            PyObject* rv;
            wxPyThreadBlocker blocker;
            rv = wxPyMakeBuffer(data, len);
            return rv;
            """)
