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

        self.stripIgnoredItems(module)

        with open(outfile, 'wb') as f:
            pickle.dump(module, f, 2)

    def stripIgnoredItems(self, item):
        """
        Strip any ignored items; they aren't useful to the module generator and
        just waste space.
        """
        delCount = 0
        for i, e in enumerate(item.items[:]):
            if e.ignored:
                del item.items[i - delCount]
                delCount += 1
            else:
                self.stripIgnoredItems(e)
