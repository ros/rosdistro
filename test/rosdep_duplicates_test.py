#!/usr/bin/env python

import os

from scripts.check_duplicates import main as check_duplicates

from .fold_block import Fold


def test():
    files = os.listdir('rosdep')
    files = filter(lambda x: x.endswith('.yaml'), files) # accept only file ends with .yaml
    files = [os.path.join('rosdep', x) for x in files] # use relative path
    with Fold() as fold:
        print("""Running 'scripts/check_duplicates.py' on all '*.yaml' in the 'rosdep' directory.
""")
        print("Checking duplicates rosdep file: %s" % files)
        assert check_duplicates(files), fold.get_message()
