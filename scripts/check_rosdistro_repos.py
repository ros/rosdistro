#!/usr/bin/env python

from __future__ import print_function

import argparse
import subprocess
import sys

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


def main(repo_type, rosdistro_name):
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
        except RuntimeError as e:
            print()
            print("Could not fetch repository '%s': %s (%s) [%s]" % (repo.name, repo.url, repo.version, e), file=sys.stderr)
    print()

    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether the referenced branches for the doc/source repositories exist')
    parser.add_argument('repo_type', choices=['doc', 'source'], help='The repository type')
    parser.add_argument('rosdistro_name', help='The ROS distro name')
    args = parser.parse_args()

    if not main(args.repo_type, args.rosdistro_name):
        sys.exit(1)
