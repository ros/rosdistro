#!/usr/bin/env python

from .cidiff import compute_unified_diff, detect_lines, DIFF_TARGET, list_changed_files
import os

from scripts.check_rosdep import main as check_rosdep

from .fold_block import Fold

def list_rosdep_files():
    files = os.listdir('rosdep')
    return [os.path.join('rosdep', f) for f in files if f.endswith('.yaml')]

def test_all():
    files = [f for f in list_rosdep_files() if f not in list_changed_files()]

    with Fold() as fold:
        print("""Running 'scripts/check_rosdep.py' on all **unchanged** '*.yaml' in the 'rosdep' directory.
If this fails you can run 'scripts/clean_rosdep_yaml.py' to help cleanup.
""")
        for f in sorted(files):
            print("Checking rosdep file: %s" % f)
            assert check_rosdep(f), fold.get_message()


def test_changed():

    files = [f for f in list_rosdep_files() if f in list_changed_files()]

    with Fold() as fold:
        print("""Running 'scripts/check_rosdep.py' on all **changed** '*.yaml' in the 'rosdep' directory.
If this fails you can run 'scripts/clean_rosdep_yaml.py' to help cleanup.
""")
        for f in sorted(files):
            print("Checking rosdep file: %s" % f)
            assert check_rosdep(f), fold.get_message()
