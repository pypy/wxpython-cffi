import os
import pickle

import etgtools.extractors as extractors
import etgtools.generators as generators
from etgtools.generators import nci, Utf8EncodingStream, textfile_open, wrapText

from buildtools.config import Config
cfg = Config(noWxConfig=True)

class CffiWrapperGenerator(generators.WrapperGeneratorBase):
    def generate(self, module):
        outfile = module.name + '.def'
        outfile = os.path.join(cfg.ROOT_DIR, 'cffi', 'def_gen', outfile)

        # We need to generate pyDocstring for some objects so later generators
        # (pi_generator) can access it. (The sip generator also does this)
        # For now just use a dummy value, this is pretty inconsequential
        for item in module.allItems():
            if not hasattr(item, 'pyDocstring'):
                item.pyDocstring = ''

        self.stripIgnoredItems(module.items)

        with open(outfile, 'wb') as f:
            pickle.dump(module, f, 2)

    def stripIgnoredItems(self, items):
        """
        Strip any ignored items; they aren't useful to the module generator and
        just waste space.
        """
        dummy = object()
        for i, e in enumerate(items):
            if e.ignored:
                items[i] = dummy

                if hasattr(e, 'overloads') and len(e.overloads) > 0:
                    # If a method is ignored, replace it with the first
                    # overload that isn't ignored
                    self.stripIgnoredItems(e.overloads)
                    if len(e.overloads) > 0:
                        e.overloads[0].overloads = e.overloads[1:]
                        items[i] = e.overloads[0]

            else:
                self.stripIgnoredItems(e.items)
                self.stripIgnoredItems(getattr(e, 'overloads', []))

        while True:
            try:
                items.remove(dummy)
            except ValueError:
                break
