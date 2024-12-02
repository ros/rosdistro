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

import argparse
import os
import sys
import yaml

from rosdep2.sources_list import load_cached_sources_list, DataSourceMatcher, SourcesListLoader, CachedDataSource
from rosdep2.lookup import RosdepLookup
from rosdep2.rospkg_loader import DEFAULT_VIEW_KEY

from rosdep2.sources_list import *


def create_default_sources():
    sources = []
    # get all rosdistro files
    basedir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
    filepath = os.path.join(basedir, 'index-v4.yaml')
    with open(filepath) as f:
        content = f.read()
    index = yaml.safe_load(content)
    for distro, metadata in index['distributions'].items():
        if metadata['distribution_status'] == 'end-of-life':
            # Skip end-of-life distributions
            continue
        distfile = 'file://' + basedir + '/' + distro + '/distribution.yaml'
        print('loading %s' % distfile)
        try:
            rds = RosDistroSource(distro)
        except KeyError:
            # When first adding a ROS distro to the repository, it won't yet
            # exist at the URL that RosDistroSource fetches from github.  When
            # trying to index it, RosDistroSource will throw a KeyError.  If we
            # see that KeyError, just ignore it and don't add the distro to the
            # list of sources.
            continue

        rosdep_data = get_gbprepo_as_rosdep_data(distro)
        sources.append(CachedDataSource('yaml', distfile, [distro], rosdep_data))

    for filename in os.listdir(os.path.join(basedir, 'rosdep')):
        if not filename.endswith('yaml'):
            continue
        filepath = os.path.join(basedir, 'rosdep', filename)
        with open(filepath) as f:
            content = f.read()
        rosdep_data = yaml.safe_load(content)
        tag = 'osx' if 'osx-' in filepath else ''
        sources.append(CachedDataSource('yaml', 'file://' + filepath, [tag], rosdep_data))
    return sources


def check_duplicates(sources, os_name, os_codename):
    # output debug info
    print('checking sources')
    for source in sources:
        print('- %s' % source.url)

    # create lookup
    sources_loader = SourcesListLoader(sources)
    lookup = RosdepLookup.create_from_rospkg(sources_loader=sources_loader)

    # check if duplicates
    print("checking duplicates")
    db_name_view = {}
    has_duplicates = False
    # to avoid merge views
    view = lookup._load_view_dependencies(DEFAULT_VIEW_KEY, lookup.loader)
    for view_key in lookup.rosdep_db.get_view_dependencies(DEFAULT_VIEW_KEY):
        db_entry = lookup.rosdep_db.get_view_data(view_key)
        print('* %s' % view_key)
        for dep_name, dep_data in db_entry.rosdep_data.items():
            # skip unknown os names
            if os_name not in dep_data.keys():
                continue
            # skip unknown os codenames
            if (
                isinstance(dep_data[os_name], dict) and
                'pip' not in dep_data[os_name].keys() and
                os_codename not in dep_data[os_name].keys()
            ):
                continue
            if dep_name in db_name_view:
                print('%s (%s, %s) is multiply defined in\n\t%s and \n\t%s\n' %
                      (dep_name, os_name, os_codename, db_name_view[dep_name], view_key))
                has_duplicates = True
            db_name_view[dep_name] = view_key
    return not has_duplicates


def main(infile):
    sources = create_default_sources()
    matcher = DataSourceMatcher.create_default()

    print('default sources')
    for source in sources:
        print('- %s' % source.url)

    # replace with infile
    for filename in infile:
        filepath = os.path.join(os.getcwd(), filename)
        with open(filepath) as f:
            content = f.read()
        rosdep_data = yaml.safe_load(content)
        # osx-homebrew uses osx tag
        tag = 'osx' if 'osx-' in filepath else ''
        model = CachedDataSource('yaml', 'file://' + filepath, [tag], rosdep_data)
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
                ['lunar', 'ubuntu', 'xenial'],
                ['', 'osx', 'homebrew']]:
        matcher.tags = tag
        print('checking with %s' % matcher.tags)
        os_name = tag[1]
        os_codename = tag[2]
        ret &= check_duplicates([x for x in sources if matcher.matches(x)],
                                os_name, os_codename)
    return ret


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether rosdep files contain duplicate ROS rules')
    parser.add_argument('infiles', nargs='*', help='input rosdep YAML file')
    args = parser.parse_args()
    if not main(args.infiles):
        sys.exit(1)
