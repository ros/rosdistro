#!/usr/bin/env python3

# Copyright 2026 R Kent James
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Add entries for new Ubuntu and Debian releases to rosdep rules that have
release-specific entries.

For each Ubuntu / Debian rule that has entries for specific releases but none
for the new release:

  - Without a '*' entry, the newest release's entry is checked against the new
    release. If all of its apt packages exist there, it is copied for the new
    release; otherwise the rule is not changed.

  - With a '*' entry, only rules with an entry for the previous release are
    considered, i.e. the newest older release used by any ROS distribution.
    That entry is copied if all of its apt packages exist in the new release;
    otherwise the rule is left to fall back to '*'.

Entries that are not plain apt package lists (pip, source, ...) are reported
but not changed.

This script was written by Opus 5.5 and not thoroughly tested. Use with caution.
"""

import argparse
import csv
import gzip
import lzma
import os
import sys
import time
import urllib.request

import yaml

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
DISTRO_INFO = '/usr/share/distro-info/%s.csv'

MIRRORS = {
    'ubuntu': ['http://archive.ubuntu.com/ubuntu', 'http://old-releases.ubuntu.com/ubuntu'],
    'debian': ['http://deb.debian.org/debian', 'http://archive.debian.org/debian'],
}
PORTS_MIRRORS = ['http://ports.ubuntu.com/ubuntu-ports', 'http://old-releases.ubuntu.com/ubuntu']
COMPONENTS = {
    'ubuntu': ['main', 'restricted', 'universe', 'multiverse'],
    'debian': ['main', 'contrib', 'non-free', 'non-free-firmware'],
}
ROS_APT_REPOS = ['http://packages.ros.org/ros2/ubuntu', 'http://packages.ros.org/ros/ubuntu']

CACHE_MAX_AGE = 24 * 60 * 60


def fetch_packages_index(urls, cache_dir, refresh):
    """
    Download (or load from cache) an apt Packages index and return its text.

    The first of the candidate urls that is cached or can be fetched is used.
    Cached copies older than CACHE_MAX_AGE seconds are downloaded again.
    """
    cache_files = [
        os.path.join(cache_dir, url.split('://', 1)[1].replace('/', '_')) for url in urls]
    candidates = []
    if not refresh:
        candidates = [
            (url, cache) for url, cache in zip(urls, cache_files)
            if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < CACHE_MAX_AGE]
    if not candidates:
        errors = []
        for url, cache_file in zip(urls, cache_files):
            try:
                with urllib.request.urlopen(url) as response:
                    data = response.read()
            except Exception as e:
                errors.append('%s: %s' % (url, e))
                continue
            print('downloaded %s' % url, file=sys.stderr)
            with open(cache_file, 'wb') as f:
                f.write(data)
            candidates = [(url, cache_file)]
            break
        else:
            raise RuntimeError('; '.join(errors))

    url, cache_file = candidates[0]
    with open(cache_file, 'rb') as f:
        data = f.read()
    if url.endswith('.xz'):
        data = lzma.decompress(data)
    elif url.endswith('.gz'):
        data = gzip.decompress(data)
    return data.decode('utf-8', errors='replace')


def load_apt_packages(codename, args, os_name):
    """Return the set of package names (including virtual packages) of a release."""
    os.makedirs(args.cache_dir, exist_ok=True)
    mirrors = MIRRORS[os_name]
    if os_name == 'ubuntu' and args.arch not in ('amd64', 'i386'):
        mirrors = PORTS_MIRRORS
    # (candidate urls, warn if none can be fetched)
    indices = []
    for suite in (codename, codename + '-updates'):
        for component in COMPONENTS[os_name]:
            path = 'dists/%s/%s/binary-%s/Packages' % (suite, component, args.arch)
            indices.append((
                ['%s/%s.%s' % (m, path, ext) for m in mirrors for ext in ('xz', 'gz')], True))
    if not args.no_ros_repo:
        for repo in ROS_APT_REPOS:
            # ROS repositories drop end-of-life releases, so a miss is expected.
            indices.append((
                ['%s/dists/%s/main/binary-%s/Packages.gz' % (repo, codename, args.arch)], False))

    packages = set()
    for urls, warn in indices:
        try:
            text = fetch_packages_index(urls, args.cache_dir, args.refresh)
        except Exception as e:
            if warn:
                print('warning: could not load %s: %s' % (urls[0], e), file=sys.stderr)
            continue
        for line in text.splitlines():
            if line.startswith('Package:'):
                packages.add(line.split(':', 1)[1].strip())
            elif line.startswith('Provides:'):
                for provided in line.split(':', 1)[1].split(','):
                    packages.add(provided.split('(')[0].strip())
    return packages


def package_exists(package, packages):
    # Strip version constraints and architecture qualifiers.
    return package.split('=')[0].split(':')[0] in packages


def release_platforms(distfile, os_name):
    """Return the release platforms of an OS in a distribution file."""
    # Only the part before the (large) repositories section is needed.
    with open(distfile) as f:
        header = f.read().split('\nrepositories:', 1)[0]
    dist = yaml.safe_load(header) or {}
    return dist.get('release_platforms', {}).get(os_name, [])


def release_order(os_name):
    """Return the codenames of an OS, oldest first, from distro-info."""
    path = DISTRO_INFO % os_name
    if not os.path.exists(path):
        sys.exit('error: %s is needed to order %s releases (install distro-info-data)' %
                 (path, os_name))
    with open(path) as f:
        return [row['series'] for row in csv.DictReader(f)]


def ros_previous_release(os_name, codename, order):
    """Return the newest release older than codename used by any ROS distribution."""
    with open(os.path.join(BASEDIR, 'index-v4.yaml')) as f:
        index = yaml.safe_load(f)
    used = set()
    for metadata in index['distributions'].values():
        for distfile in metadata['distribution']:
            used.update(release_platforms(os.path.join(BASEDIR, distfile), os_name))
    older = [r for r in used if r in order and order.index(r) < order.index(codename)]
    if not older:
        sys.exit('error: no ROS distribution used a %s release older than %s' % (os_name, codename))
    return max(older, key=order.index)


def find_os_block_children(lines, key, os_name):
    """
    Return (children, end) for the os_name block of a top-level key.

    children is a list of (line index, codename) for the entries in the block,
    and end is the index of the line after the block.
    """
    start = next(i for i, line in enumerate(lines) if line.startswith(key + ':') or
                 line.startswith("'%s':" % key))
    i = start + 1
    while i < len(lines) and lines[i].startswith(' '):
        if lines[i].rstrip('\n') == '  %s:' % os_name:
            break
        i += 1
    else:
        return None, None
    children = []
    i += 1
    while i < len(lines) and lines[i].startswith('    '):
        if not lines[i].startswith('     '):
            children.append((i, lines[i].strip().split(':', 1)[0].strip('\'"')))
        i += 1
    return children, i


def format_entry(codename, packages):
    return '    %s: [%s]\n' % (codename, ', '.join(packages))


def plan_changes(rules, os_name, codename, packages):
    """Return a list of (key, new packages, message) for one OS."""
    order = release_order(os_name)
    if codename not in order:
        sys.exit('error: unknown %s release %s' % (os_name, codename))
    previous_release = ros_previous_release(os_name, codename, order)

    def age(release):
        return order.index(release) if release in order else -1

    changes = []
    for key in sorted(rules):
        rule = rules[key]
        os_rule = rule.get(os_name) if isinstance(rule, dict) else None
        if not isinstance(os_rule, dict) or codename in os_rule:
            continue
        releases = [r for r in os_rule if r != '*']
        if not releases or any(k in os_rule for k in ('apt', 'pip', 'source')):
            continue
        # Only releases older than the new one.
        releases = [r for r in releases if age(r) < order.index(codename)]
        if not releases:
            continue

        has_star = '*' in os_rule
        if has_star:
            if previous_release not in os_rule:
                continue
            source = previous_release
        else:
            source = max(releases, key=age)
        entry = os_rule[source]

        if entry is not None and not isinstance(entry, list):
            print('%s: %s %s entry is not an apt package list, skipped' % (key, os_name, source))
            continue
        missing = [p for p in entry or [] if not package_exists(p, packages)]
        if entry and not missing:
            changes.append((key, entry, 'copied from %s' % source))
        else:
            fallback = "left to '*'" if has_star else 'not changed'
            if entry:
                print('%s: %s %s entry not available in %s (%s), %s' % (
                    key, os_name, source, codename, ', '.join(missing), fallback))
            else:
                print('%s: %s %s entry is empty, %s' % (key, os_name, source, fallback))
    return changes


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--ubuntu', default='resolute',
        help='new Ubuntu release to add entries for (default: %(default)s)')
    parser.add_argument(
        '--debian', default='trixie',
        help='new Debian release to add entries for (default: %(default)s)')
    parser.add_argument(
        '--file', default=os.path.join(BASEDIR, 'rosdep', 'python.yaml'),
        help='rosdep file to update (default: rosdep/python.yaml)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='only show the entries that would be added')
    parser.add_argument(
        '--arch', default='amd64',
        help='architecture of the apt package indices (default: %(default)s)')
    parser.add_argument(
        '--no-ros-repo', action='store_true',
        help='do not count packages from packages.ros.org as existing')
    parser.add_argument(
        '--cache-dir',
        default=os.path.join(
            os.environ.get('XDG_CACHE_HOME', os.path.expanduser('~/.cache')),
            'rosdistro-apt-indices'),
        help='directory for downloaded apt indices (default: %(default)s)')
    parser.add_argument(
        '--refresh', action='store_true',
        help='re-download apt indices even if the cached copies are recent')
    args = parser.parse_args(argv)

    with open(args.file) as f:
        lines = f.readlines()
    rules = yaml.safe_load(''.join(lines))

    # (line index, text) of lines to insert
    insertions = []
    for os_name, codename in (('ubuntu', args.ubuntu), ('debian', args.debian)):
        available = load_apt_packages(codename, args, os_name)
        if not available:
            sys.exit('error: no apt package indices could be loaded for %s %s' % (os_name, codename))
        for key, packages, message in plan_changes(rules, os_name, codename, available):
            print('%s: %s %s: [%s] (%s)' % (
                key, os_name, codename, ', '.join(packages), message))
            children, end = find_os_block_children(lines, key, os_name)
            if children is None:
                print('warning: could not find the %s block of %s, not changed' % (os_name, key),
                      file=sys.stderr)
                continue
            position = next((i for i, name in children if name > codename), end)
            insertions.append((position, format_entry(codename, packages)))

    sys.stdout.flush()
    print('%d entries to add' % len(insertions), file=sys.stderr)
    if args.dry_run or not insertions:
        return 0
    for position, text in sorted(insertions, reverse=True):
        lines.insert(position, text)
    with open(args.file, 'w') as f:
        f.writelines(lines)
    print('updated %s' % os.path.relpath(args.file), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
