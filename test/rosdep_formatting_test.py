#!/usr/bin/env python

import os

from scripts.check_rosdep import main as check_rosdep


def test():
    files = os.listdir('rosdep')

    print("""
Running 'scripts/check_rosdep.py' on all *.yaml in the rosdep directory.
If this fails you can run 'scripts/clean_rosdep.py' to help cleanup.
""")

    for f in files:
        fname = os.path.join('rosdep', f)
        if not f.endswith('.yaml'):
            print("Skipping rosdep check of file %s" % fname)
            continue
        print("Checking rosdep file %s" % fname)
        assert check_rosdep(fname)
