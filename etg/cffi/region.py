def run(module):
    c = module.find('wxRegion')

    # TODO: Add a ctor like in sip/region.py. Consider using Array to automate
    #       conversion instead of trying to replicate ObjArrayHelperTemplate.
    #       (Requires fixing Array for wrapped types first.)
