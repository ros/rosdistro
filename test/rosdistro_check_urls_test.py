#!/usr/bin/env python

import os

from rosdistro import get_index
from scripts import eol_distro_names
from scripts.check_rosdistro_urls import main as check_rosdistro_urls

from .fold_block import Fold

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_rosdistro_urls():
    index_url = 'file://' + FILES_DIR + '/index.yaml'
    index = get_index(index_url)
    failed_distros = []
    fold_blocks = []
    for distro_name in sorted(index.distributions.keys()):
        if distro_name in eol_distro_names:
            continue
        with Fold() as fold:
            print("""Checking if the distribution files of '%s' contain valid urls for known hosting services.
If this fails you can run 'scripts/check_rosdistro_urls.py file://`pwd`/%s %s' to perform the same check locally.
""" % (distro_name, 'index.yaml', distro_name))
            if not check_rosdistro_urls(index_url, distro_name):
                failed_distros.append(distro_name)
                fold_blocks.append(fold.get_block_name())
    assert not failed_distros, "There were problems with urls in the distribution files for these distros: %s, see folded blocks for details: %s" % (failed_distros, fold_blocks)
