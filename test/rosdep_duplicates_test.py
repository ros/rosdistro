#!/usr/bin/env python

import os

from scripts.check_duplicates import main as check_duplicates

from .fold_block import Fold


def test_rosdep_duplicates():
    files = os.listdir('rosdep')
    files = [x for x in files if x.endswith('.yaml')]  # accept only files ending with .yaml
    files = [os.path.join('rosdep', x) for x in files]  # use relative path
    with Fold() as fold:
        print("Running 'scripts/check_duplicates.py' on all '*.yaml' in the 'rosdep' directory.")
        print('Checking duplicates rosdep file: %s' % files)
        assert check_duplicates(files), fold.get_message()
