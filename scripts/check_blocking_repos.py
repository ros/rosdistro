#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys

import rosdistro
from rosdistro.dependency_walker import DependencyWalker


def is_released(repository, dist_file):
    return repository in dist_file.repositories and \
        dist_file.repositories[repository].release_repository is not None and \
        dist_file.repositories[repository].release_repository.version is not None


parser = argparse.ArgumentParser(
    description='Get unreleased repos and their dependencies.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '--rosdistro', metavar='ROS_DISTRO',
    help='The ROS distribution to check packages for')

# If not specified, check for all repositories in the previous distribution
parser.add_argument(
    '--repositories',
    metavar='REPOSITORY_NAME', nargs='*',
    help='Unreleased repositories to check dependencies for')

parser.add_argument(
    '--depth',
    metavar='depth', type=int,
    help='Maxmium depth to crawl the dependency tree')

parser.add_argument(
    '--comparison-rosdistro',
    metavar='ROS_DISTRO',
    dest='comparison',
    help='The rosdistro with which to compare')

args = parser.parse_args()

distro_key = args.rosdistro
repo_names_argument = args.repositories
prev_distro_key = None

index = rosdistro.get_index(rosdistro.get_index_url())
valid_distro_keys = index.distributions.keys()
valid_distro_keys.sort()
if distro_key is None:
    distro_key = valid_distro_keys[-1]

# Find the previous distribution to the current one
try:
    i = valid_distro_keys.index(distro_key)
except ValueError:
    print('Distribution key (%s) not found in list of valid distributions.' % distro_key, file=sys.stderr)
    print('Valid rosdistros are %s.' % valid_distro_keys, file=sys.stderr)
    exit(-1)
if i == 0 and not args.comparison:
    print('No previous distribution found.', file=sys.stderr)
    exit(-1)

if args.comparison:
    valid_comparison_keys = valid_distro_keys[:]
    valid_comparison_keys.remove(distro_key)
    if args.comparison not in valid_comparison_keys:
        print('Invalid rosdistro [%s] selected for comparison to [%s].' % (args.comparison, distro_key),
              file=sys.stderr)
        print('Valid rosdistros are %s.' % valid_comparison_keys, file=sys.stderr)
        exit(-1)
    prev_distro_key = args.comparison
else:
    prev_distro_key = valid_distro_keys[i - 1]

cache = rosdistro.get_distribution_cache(index, distro_key)
distro_file = cache.distribution_file

prev_cache = rosdistro.get_distribution_cache(index, prev_distro_key)
prev_distribution = rosdistro.get_cached_distribution(
    index, prev_distro_key, cache=prev_cache)

prev_distro_file = prev_cache.distribution_file

dependency_walker = DependencyWalker(prev_distribution)

if repo_names_argument is None:
    # Check missing dependencies for packages that were in the previous
    # distribution that have not yet been released in the current distribution
    # Filter repos without a version or a release repository
    repo_names_argument = prev_distro_file.repositories.keys()

prev_repo_names = set(
    repo for repo in repo_names_argument if is_released(repo, prev_distro_file))

keys = distro_file.repositories.keys()
current_repo_names = set(
    repo for repo in keys if is_released(repo, distro_file))

# Print the repositories that will be eliminated from the input
eliminated_repositories = prev_repo_names.intersection(
    current_repo_names)
if len(eliminated_repositories) > 0:
    print('Ignoring inputs which have already been released:')
    print('\n'.join(
        sorted('\t{0}'.format(repo) for repo in eliminated_repositories)))

repo_names_set = prev_repo_names.difference(
    current_repo_names)
invalid_names = set(repo_names_argument).difference(prev_repo_names)

if len(repo_names_set) == 0:
    print('All inputs are invalid or were already released in {0}.'.format(
        distro_key))
    if invalid_names:
        print('Could no resolve: %s in %s' % (list(invalid_names), prev_distro_key), file=sys.stderr)
        exit(1)
    print('Exiting without checking any dependencies.')
    exit(0)

repo_names = list(repo_names_set)


# Get a list of currently released packages
current_package_names = set(
    pkg for repo in current_repo_names
    for pkg in distro_file.repositories[repo].release_repository.package_names)

# Construct a dictionary where keys are repository names and values are a list
# of the missing dependencies for that repository

blocked_repos = {}
unblocked_repos = set()
total_blocking_repos = set()

for repository_name in repo_names:
    repo = prev_distro_file.repositories[repository_name]
    release_repo = repo.release_repository
    package_dependencies = set()
    packages = release_repo.package_names
    # Accumulate all dependencies for those packages
    for package in packages:
        recursive_dependencies = dependency_walker.get_recursive_depends(
            package, ['build', 'run', 'buildtool'], ros_packages_only=True,
            limit_depth=args.depth)
        package_dependencies = package_dependencies.union(
            recursive_dependencies)

    # For all package dependencies, check if they are released yet
    unreleased_pkgs = package_dependencies.difference(
        current_package_names)
    # remove the packages which this repo provides.
    unreleased_pkgs = unreleased_pkgs.difference(packages)
    # Now get the repositories for these packages.
    blocking_repos = set(prev_distro_file.release_packages[pkg].repository_name
                         for pkg in unreleased_pkgs)
    if len(blocking_repos) == 0:
        unblocked_repos.add(repository_name)
    else:
        # Get the repository for the unreleased packages
        blocked_repos[repository_name] = blocking_repos
        total_blocking_repos |= blocking_repos

unblocked_blocking_repos = total_blocking_repos.intersection(unblocked_repos)
unblocked_leaf_repos = unblocked_repos.difference(unblocked_blocking_repos)

# Double-check repositories that we think are leaf repos
for repo in unblocked_leaf_repos:
    # Check only one level of depends_on
    depends_on = dependency_walker.get_depends_on(package, 'build') | \
        dependency_walker.get_depends_on(package, 'run') | \
        dependency_walker.get_depends_on(package, 'buildtool')
    if len(depends_on) != 0:
        # There are packages that depend on this "leaf", but we didn't find
        # them initially because they weren't related to our inputs
        unblocked_blocking_repos.add(repo)
unblocked_leaf_repos = unblocked_leaf_repos.difference(
    unblocked_blocking_repos)

if len(blocked_repos.keys()) > 0:
    print('The following repos cannot be released because of unreleased '
          'dependencies:')
    for blocked_repo_name in sorted(blocked_repos.keys()):
        unreleased_repos = blocked_repos[blocked_repo_name]
        print('\t{0}:'.format(blocked_repo_name))

        print('\n'.join(
            sorted('\t\t{0}'.format(repo) for repo in unreleased_repos)))

if len(unblocked_leaf_repos) > 0:
    print('The following repos can be released, but do not block other repos:')
    print('\n'.join(
        sorted('\t{0}'.format(repo) for repo in unblocked_leaf_repos)))

if len(unblocked_blocking_repos) > 0:
    print('The following repos can be released, and are blocking other repos:')
    print('\n'.join(
        sorted('\t{0}'.format(repo) for repo in unblocked_blocking_repos)))

if len(invalid_names):
    print('Could no resolve the following arguments in %s: ' % prev_distro_key, file=sys.stderr)
    print('\n'.join(
        sorted('\t{0}'.format(repo) for repo in invalid_names)), file=sys.stderr)
    exit(1)
