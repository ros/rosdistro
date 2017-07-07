#!/usr/bin/env python
# Copyright (c) 2017, Open Source Robotics Foundation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import argparse
import os
import sys
import yaml

# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# With modifications
#           (C) 2013 Paul M <pmathieu@willowgarage.com>

codeCodes = {
    'black':     '0;30',     'bright gray':   '0;37',
    'blue':      '0;34',     'white':         '1;37',
    'green':     '0;32',     'bright blue':   '1;34',
    'cyan':      '0;36',     'bright green':  '1;32',
    'red':       '0;31',     'bright cyan':   '1;36',
    'purple':    '0;35',     'bright red':    '1;31',
    'yellow':    '0;33',     'bright purple': '1;35',
    'dark gray': '1;30',     'bright yellow': '1;33',
    'normal':    '0'
}


def printc(text, color):
    """Print in color."""
    if sys.stdout.isatty():
        print("\033["+codeCodes[color]+"m"+text+"\033[0m")
    else:
        print(text)


def print_test(msg):
    printc(msg, 'yellow')


def print_err(msg):
    printc('  ERR: ' + msg, 'red')

###
###
from rosdep2.sources_list import load_cached_sources_list, DataSourceMatcher, SourcesListLoader, CachedDataSource
from rosdep2.lookup import RosdepLookup
from rosdep2.rospkg_loader import DEFAULT_VIEW_KEY

from rosdep2.sources_list import *

def create_default_sources():
    sources = []
    # get all rosdistro files
    basedir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    filepath = os.path.join(basedir, 'index.yaml')
    with open(filepath) as f:
        index = yaml.load(f.read())
        for distro in index['distributions']:
            distfile = 'file://'+basedir+'/'+distro+'/distribution.yaml'
            print_test("loading %s" % (distfile))
            rds = RosDistroSource(distro)
            rosdep_data = get_gbprepo_as_rosdep_data(distro)
            sources.append(CachedDataSource('yaml', distfile, [distro], rosdep_data))
    for filename in os.listdir(os.path.join(basedir,'rosdep')):
        if filename.endswith('yaml'):
            filepath = os.path.join(basedir, 'rosdep', filename)
            with open(filepath) as f:
                rosdep_data = yaml.load(f.read())
            tag = 'osx' if 'osx-' in filepath else ''
            sources.append(CachedDataSource('yaml', 'flie:/'+filepath, [tag], rosdep_data))
    return sources


def check_duplicates(sources):
    ret = True
    # output debug info
    print_test("checking sources")
    for source in sources:
        print_test("- %s" % source.url)

    # create loopkup
    sources_loader = SourcesListLoader(sources)
    lookup = RosdepLookup.create_from_rospkg(sources_loader=sources_loader)

    #
    db_name_view = dict()

    # check if duplicates
    print_test("checking duplicates")
    view = lookup.get_rosdep_view(DEFAULT_VIEW_KEY, verbose=None) # to call init
    for view_key in lookup.rosdep_db.get_view_dependencies(DEFAULT_VIEW_KEY):
        db_entry=lookup.rosdep_db.get_view_data(view_key)
        print_test("* %s" % view_key)
        for dep_name, dep_data in db_entry.rosdep_data.items():
            if dep_name in db_name_view:
                print_err("%s is multiply defined in\n\t%s and \n\t%s\n"%(dep_name, db_name_view[dep_name], view_key))
                ret = False
            db_name_view[dep_name] = view_key
    return ret

def main(infile):

    # surces
    sources = create_default_sources()
    matcher = DataSourceMatcher.create_default()

    print_test("default sources")
    for source in sources:
        print_test("- %s" % source.url)

    # replace with infile
    for filename in infile:
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath) as f:
            rosdep_data = yaml.load(f.read())
        # osx-homebrow uses xos tag
        tag = 'osx' if 'osx-' in filepath else ''
        model = CachedDataSource('yaml', 'flie:/'+filepath, [tag], rosdep_data)
        # add sources if not exists
        if not [x for x in sources if os.path.basename(filename) == os.path.basename(x.url)]:
            sources.append(model)
        else:
            # remove files with same filename
            sources = [model if os.path.basename(filename) == os.path.basename(x.url) else x for x in sources]

    ret = True
    for tag in [['indigo', 'ubuntu', 'trusty'],
                ['jade', 'ubuntu', 'trusty'],
                ['kinetic', 'ubuntu', 'xenial'],
                ['lunar', 'ubuntu', 'xenial']]:
        matcher.tags = tag
        print_test('checking with %s'%(matcher.tags))
        sources = [x for x in sources if matcher.matches(x)]
        ret = ret & check_duplicates(sources)
    return ret

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether rosdep files contains duplicate ROS rules')
    parser.add_argument('infiles', nargs='*', help='input rosdep YAML file')
    args = parser.parse_args()
    if not main(args.infiles):
        sys.exit(1)

