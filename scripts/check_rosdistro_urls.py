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
import sys

from rosdistro import get_distribution_file, get_index


def main(index_url, rosdistro_name):
    index = get_index(index_url)
    try:
        distribution_file = get_distribution_file(index, rosdistro_name)
    except RuntimeError as e:
        print("Could not load distribution file for distro '%s': %s" % (rosdistro_name, e), file=sys.stderr)
        return False

    success = True
    for repo_name in sorted(distribution_file.repositories.keys()):
        sys.stdout.write('.')
        sys.stdout.flush()
        repo = distribution_file.repositories[repo_name]
        repos = [repo.release_repository, repo.source_repository, repo.doc_repository]
        for repo in [r for r in repos if r]:
            if repo.url.startswith('file://'):
                print()
                print("Repository '%s' with url '%s' must not be a local 'file://' url" % (repo_name, repo.url), file=sys.stderr)
                success = False
            if repo.type == 'git':
                prefixes = ['http://github.com/', 'git@github.com:']
                for prefix in prefixes:
                    if repo.url.startswith(prefix):
                        print()
                        print("Repository '%s' with url '%s' must use 'https://github.com/%s' instead" % (repo_name, repo.url, repo.url[len(prefix):]), file=sys.stderr)
                        success = False
                for prefix in prefixes + ['https://github.com/']:
                    if repo.url.startswith(prefix) and not repo.url.endswith('.git'):
                        print()
                        print("Repository '%s' with url '%s' should end with `.git` but does not." % (repo_name, repo.url))
                        success = False
    print()

    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether the referenced URLs have the expected pattern for known hosts')
    parser.add_argument('index_url', help='The url of the index.yaml file')
    parser.add_argument('rosdistro_name', help='The ROS distro name')
    args = parser.parse_args()

    if not main(args.index_url, args.rosdistro_name):
        sys.exit(1)
