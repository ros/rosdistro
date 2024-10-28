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
import shutil
import subprocess
import sys
import tempfile

from catkin_pkg.packages import find_package_paths
from rosdistro import get_distribution_file, get_index, get_index_url


def check_git_repo(url, version):
    cmd = ['git', 'ls-remote', url]
    try:
        output = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid git repo url')

    if version:
        for line in output.splitlines():
            if line.endswith('/%s' % version):
                return
        raise RuntimeError('version not found')


def check_hg_repo(url, version):
    cmd = ['hg', 'identify', url]
    if version:
        cmd.extend(['-r', version])
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if not version:
            raise RuntimeError('not a valid hg repo url')
        cmd = ['hg', 'identify', url]
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('not a valid hg repo url')
        raise RuntimeError('version not found')


def check_svn_repo(url, version):
    cmd = ['svn', '--non-interactive', '--trust-server-cert', 'info', url]
    if version:
        cmd.extend(['-r', version])
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid svn repo url')


def clone_git_repo(url, version, path):
    cmd = ['git', 'clone', url, '-b', version, '-q']
    try:
        subprocess.check_call(cmd, cwd=path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid git repo url')


def clone_hg_repo(url, version, path):
    cmd = ['hg', 'clone', url, '-q']
    if version:
        cmd.extend(['-b', version])
    try:
        subprocess.check_call(cmd, stderr=subprocess.STDOUT, cwd=path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid hg repo url')


def checkout_svn_repo(url, version, path):
    cmd = ['svn', '--non-interactive', '--trust-server-cert', 'checkout', url, '-q']
    if version:
        cmd.extend(['-r', version])
    try:
        subprocess.check_call(cmd, stderr=subprocess.STDOUT, cwd=path)
    except subprocess.CalledProcessError as e:
        raise RuntimeError('not a valid svn repo url')


def main(repo_type, rosdistro_name, check_for_wet_packages=False):
    index = get_index(get_index_url())
    try:
        distribution_file = get_distribution_file(index, rosdistro_name)
    except RuntimeError as e:
        print("Could not load distribution file for distro '%s': %s" % (rosdistro_name, e), file=sys.stderr)
        return False

    for repo_name in sorted(distribution_file.repositories.keys()):
        sys.stdout.write('.')
        sys.stdout.flush()
        repo = distribution_file.repositories[repo_name]
        if repo_type == 'doc':
            repo = repo.doc_repository
        if repo_type == 'source':
            repo = repo.source_repository
        if not repo:
            continue
        try:
            if (repo.type == 'git'):
                check_git_repo(repo.url, repo.version)
            elif (repo.type == 'hg'):
                check_hg_repo(repo.url, repo.version)
            elif (repo.type == 'svn'):
                check_svn_repo(repo.url, repo.version)
            else:
                print()
                print("Unknown type '%s' for repository '%s'" % (repo.type, repo.name), file=sys.stderr)
                continue
        except RuntimeError as e:
            print()
            print("Could not fetch repository '%s': %s (%s) [%s]" % (repo.name, repo.url, repo.version, e), file=sys.stderr)
            continue

        if check_for_wet_packages:
            path = tempfile.mkdtemp()
            try:
                if repo.type == 'git':
                    clone_git_repo(repo.url, repo.version, path)
                elif repo.type == 'hg':
                    clone_hg_repo(repo.url, repo.version, path)
                elif repo.type == 'svn':
                    checkout_svn_repo(repo.url, repo.version, path)
            except RuntimeError as e:
                print()
                print("Could not clone repository '%s': %s (%s) [%s]" % (repo.name, repo.url, repo.version, e), file=sys.stderr)
                continue
            else:
                package_paths = find_package_paths(path)
                if not package_paths:
                    print()
                    print("Repository '%s' (%s [%s]) does not contain any wet packages" % (repo.name, repo.url, repo.version), file=sys.stderr)
                    continue
            finally:
                shutil.rmtree(path)

    print()

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether the referenced branches for the doc/source repositories exist')
    parser.add_argument('repo_type', choices=['doc', 'source'], help='The repository type')
    parser.add_argument('rosdistro_name', help='The ROS distro name')
    parser.add_argument('--check-for-wet-packages', action='store_true', help='Check if the repository contains wet packages rather then dry packages')
    args = parser.parse_args()

    if not main(args.repo_type, args.rosdistro_name, args.check_for_wet_packages):
        sys.exit(1)
