#!/usr/bin/env python

import os

from scripts.check_rosdistro import main as check_rosdist


def test():
    files = os.listdir('releases')

    print("""
Running 'scripts/check_rosdistro.py' on all *.yaml in the releases directory.
If this fails you can run 'scripts/check_rosdistro.py' to perform the same check locally.
""")

    for f in files:
        fname = os.path.join('releases', f)
        if not f.endswith('.yaml'):
            print("Skipping rosdistro check of file %s" % fname)
            continue
        print("Checking rosdistro file %s" % fname)
        assert check_rosdist(fname)
