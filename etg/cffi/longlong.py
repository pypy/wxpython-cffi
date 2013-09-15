import etgtools
import etgtools.tweaker_tools as tools

PACKAGE   = "wx"
MODULE    = "_core"
NAME      = "longlong"   # Base name of the file to generate to for this script
DOCSTRING = ""


#---------------------------------------------------------------------------

def run():
    module = etgtools.ModuleDef(PACKAGE, MODULE, NAME, DOCSTRING)

    # Unlike the sip backend, no attempts are made here to support systems that
    # don't have native 64-bit integers
    module.addItem(etgtools.MappedTypeDef_cffi(
        name='wxLongLong', cType='long long',
        py2c="return (int(py_obj), None)",
        c2cpp="""
        return new wxLongLong(cdata);
        """,

        cpp2c="""
        return cpp_obj->GetValue();
        """,
        c2py="return cdata",

        instancecheck="return isinstance(py_obj, numbers.Number)"))

    #-----------------------------------------------------------------
    tools.doCommonTweaks(module)
    tools.runGenerators(module)


#---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
