#!/usr/bin/env python

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
