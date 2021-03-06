import etgtools

def run(module):
    c = module.find('wxConfigBase')

    # TODO: The sip backend replaces these methods with custom ones that return
    # a manually constructed 3-tuple. Instead, we'll attempt to just set the
    # approporiate parameters as out/inOut, which should have the same effect.

    c.find('GetFirstGroup.str').out = True
    c.find('GetFirstGroup.index').out = True

    c.find('GetNextGroup.str').out = True
    c.find('GetNextGroup.index').inOut = True

    c.find('GetFirstEntry.str').out = True
    c.find('GetFirstEntry.index').out = True

    c.find('GetNextEntry.str').out = True
    c.find('GetNextEntry.index').inOut = True
