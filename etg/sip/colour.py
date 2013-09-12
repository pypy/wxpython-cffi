def run(module):
    c = module.find('wxColour')

    c.addCppMethod('PyObject*', 'Get', '(bool includeAlpha=true)', """\
        int red = -1;
        int green = -1;
        int blue = -1;
        int alpha = wxALPHA_OPAQUE;
        if (self->IsOk()) {
            red =   self->Red();
            green = self->Green();
            blue =  self->Blue();
            alpha = self->Alpha();
        }
        if (includeAlpha)
            return sipBuildResult(0, "(iiii)", red, green, blue, alpha);
        else
            return sipBuildResult(0, "(iii)", red, green, blue);
    """, briefDoc="""\
        Get(includeAlpha=False) -> (r,g,b) or (r,g,b,a)\n
        Returns the RGB intensity values as a tuple, optionally the alpha value as well.""")
