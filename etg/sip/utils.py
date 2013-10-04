import etgtools

def run(module):
     # Forward declarations for classes that are referenced but not defined
    # yet.
    #
    # TODO: Remove these when the classes are added for real.
    # TODO: Add these classes for real :-)
    module.insertItem(0, etgtools.WigCode("""\
        // forward declarations
        class wxPalette;
        class wxExecuteEnv;
        """))


