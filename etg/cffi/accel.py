def run(module):
    c = module.find('wxAcceleratorTable')

    # Replace the implementation of the AcceleratorTable ctor so it can
    # accept a Python sequence of tuples or AcceleratorEntry objects like
    # Classic does. Using the arraySize and array annotations does let us
    # pass a list of entries, but they have to already be AccelertorEntry
    # obejcts. We want to allow Items in the list to be either
    # wx.AcceleratorEntry items or a 3-tuple containing the values to pass to
    # the wx.AcceleratorEntry ctor.

    # Ignore the current constructor
    c.find('wxAcceleratorTable').findOverload('entries').ignore()

    # TODO: create the new ctor using a CppMethodDef_cffi
