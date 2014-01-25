#!/usr/bin/env python

import os

from rosdistro import get_index
from scripts.check_rosdistro_urls import main as check_rosdistro_urls

FILES_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def test_rosdistro_urls():
    index_url = 'file://' + FILES_DIR + '/index.yaml'
    index = get_index(index_url)
    success = True
    for distro_name in index.distributions.keys():
        print("""
Checking if distribution.yaml contains valid urls for known hosting services.
If this fails you can run 'scripts/check_rosdistro_urls.py file://`pwd`/%s %s' to perform the same check locally.
""" % ('index.yaml', distro_name))
        success &= check_rosdistro_urls(index_url, distro_name)
    assert success
