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
Automatically apply classes of fixes to rosdep rule files.

Package lookups, platform definitions and repository sources come from
test/rosdep_repo_check, so a fix only adds packages that the rosdep
repository check run on pull requests will also find.

A typical call, from the top of the repository:

  scripts/autofix_rosdep.py --dry-run rosdep/base.yaml

Available fixes:

  add-releases
    Add entries for the supported Ubuntu and Debian releases (supported_versions
    in test/rosdep_repo_check/config.yaml) to rules that have release-specific
    entries but none for a supported release. Releases are handled oldest
    first, so an entry added for one release can be copied to the next.

      - Without a '*' entry, the entry of the newest release older than the
        missing one is checked against the missing release. If all of its
        packages exist there, it is copied; otherwise the rule is not changed.

      - With a '*' entry, only rules with an entry for the previous supported
        release are considered. A missing release is assumed to fall back to
        '*' by accident, so that entry is copied if all of its packages exist
        in the missing release; otherwise the rule is left to fall back to '*'.

    Entries that are not plain package lists (pip, source, ...) are reported
    but not changed.

  ubuntu-simple
    Remove one line 'ubuntu: [...]' entries of rules when no current Ubuntu
    release provides all of the listed packages. Current releases are the LTS
    and supported releases from --ubuntu-first-current (default bionic) up to
    the newest supported release. Virtual packages (Provides: in the package
    index) count as available, since apt can install them. Entries are only
    removed if they are not available on arm64 or armhf either (from
    ports.ubuntu.com and the ROS bootstrap repository); if one of those
    indices cannot be read, the entry is kept. Rules with no other entries are
    removed entirely.

    With --last-release, each removal also reports the newest older release
    that had all of its packages, searching backward from the first current
    release. Only the main, universe and multiverse components of the release
    pocket are read, from archive.ubuntu.com or old-releases.ubuntu.com. The
    first run downloads these older indices, which can take several minutes.

Downloaded package indices are saved in the artifacts folder at the top of
the repository. If a download fails or times out, the saved copy from a
previous run is used instead, with a warning. --use-artifacts uses the saved
copies without downloading, and only downloads indices that have no saved
copy.

Each run, also with --dry-run, writes a report to artifacts/fixes.txt: the
command line, then for each file the changes made, grouped by kind.

This script was written by Opus 5.5 and not thoroughly tested. Use with caution.
"""

import argparse
import csv
import gzip
import io
import os
import re
import shlex
import sys
import time

import yaml

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
sys.path.insert(0, os.path.join(BASEDIR, 'test'))

from rosdep_repo_check import deb  # noqa: E402
from rosdep_repo_check import find_package  # noqa: E402
from rosdep_repo_check import open_compressed_url  # noqa: E402
from rosdep_repo_check.config import load_config  # noqa: E402
from rosdep_repo_check.yaml import AnnotatedSafeLoader  # noqa: E402

ARTIFACTS_DIR = os.path.join(BASEDIR, 'artifacts')
FIXES_REPORT = os.path.join(ARTIFACTS_DIR, 'fixes.txt')
DISTRO_INFO = '/usr/share/distro-info/%s.csv'
DOWNLOAD_TIMEOUT = 10
# Indices of old Ubuntu releases, for --last-release. Releases past their end
# of life are only on old-releases, which is slow.
OLD_UBUNTU_MIRRORS = ('http://archive.ubuntu.com/ubuntu', 'http://old-releases.ubuntu.com/ubuntu')
OLD_UBUNTU_COMPONENTS = ('main', 'universe', 'multiverse')
OLD_DOWNLOAD_TIMEOUT = 60
# Ubuntu architectures, besides the supported one, whose packages ubuntu-simple
# keeps entries for. Their indices are not on archive.ubuntu.com.
UBUNTU_PORTS_ARCHES = ('arm64', 'armhf')
UBUNTU_PORTS_MIRROR = 'http://ports.ubuntu.com/ubuntu-ports'
ROS_BOOTSTRAP = 'http://repos.ros.org/repos/ros_bootstrap'


class RuleFile:
    """A rosdep file with its parsed rules and the lines fixes will insert."""

    def __init__(self, path):
        self.path = path
        with open(path) as f:
            self.lines = f.readlines()
        # Keys are annotated with the (1-based) line they are defined on.
        self.rules = yaml.load(''.join(self.lines), Loader=AnnotatedSafeLoader)
        # (line index, text) of lines to insert
        self.insertions = []
        # line indices of lines to remove
        self.removals = set()
        # (kind, description) of the changes made by fixes, kind from CHANGE_KINDS
        self.changes = []

    def report(self, kind, text):
        print(text)
        self.changes.append((kind, text))

    def insert(self, index, text):
        self.insertions.append((index, text))

    def remove(self, index):
        self.removals.add(index)

    def write(self):
        # Removed lines are dropped last, so insertion indices stay valid.
        lines = [None if i in self.removals else line for i, line in enumerate(self.lines)]
        # Lines inserted at the same index end up in alphabetical order.
        for index, text in sorted(self.insertions, reverse=True):
            lines.insert(index, text)
        with open(self.path, 'w') as f:
            f.writelines(line for line in lines if line is not None)


def artifact_path(url):
    """Return the path of the saved (gzip compressed) copy of a download."""
    name = url.split('://', 1)[1].replace('/', '_')
    if not name.endswith('.gz'):
        name += '.gz'
    return os.path.join(ARTIFACTS_DIR, name)


def open_artifact_url(url, use_artifacts, timeout=DOWNLOAD_TIMEOUT):
    """
    Open a package index URL, saving a copy of it in the artifacts folder.

    If use_artifacts is set and a previous run saved a copy, that copy is used
    without downloading. If the download fails or times out, a saved copy is
    used instead.
    """
    path = artifact_path(url)
    if use_artifacts and os.path.exists(path):
        return gzip.open(path, 'rb')
    try:
        with open_compressed_url(url, retry=0, timeout=timeout) as f:
            data = f.read()
    except (OSError, EOFError) as e:
        if not os.path.exists(path):
            raise
        print('warning: could not download %s (%s), using the copy saved %s' % (
            url, e, time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(path)))),
            file=sys.stderr)
        return gzip.open(path, 'rb')
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with gzip.open(path + '.tmp', 'wb', compresslevel=1) as f:
        f.write(data)
    os.replace(path + '.tmp', path)
    return io.BytesIO(data)


def distro_info(os_name):
    """Return the distro-info rows of the releases of an OS, oldest first."""
    path = DISTRO_INFO % os_name
    if not os.path.exists(path):
        sys.exit('error: %s is needed to order %s releases (install distro-info-data)' %
                 (path, os_name))
    with open(path) as f:
        return list(csv.DictReader(f))


def release_order(os_name):
    """Return the codenames of an OS, oldest first, from distro-info."""
    return [row['series'] for row in distro_info(os_name)]


def entry_position(rule_file, os_rule, codename):
    """Return (line index, indent) at which to insert an entry for codename in os_rule."""
    # Entries added by fixes have no line number.
    children = [k for k in os_rule if hasattr(k, '__line__')]
    indent = rule_file.lines[children[0].__line__ - 1]
    indent = indent[:len(indent) - len(indent.lstrip())]
    following = [k for k in children if k > codename]
    if following:
        return min(k.__line__ for k in following) - 1, indent
    # After the last entry, including any lines nested under it.
    index = max(k.__line__ for k in children)
    while index < len(rule_file.lines) and \
            rule_file.lines[index].startswith(indent + ' '):
        index += 1
    return index, indent


def fix_add_releases(config, rule_file, args):
    """Add entries for supported Ubuntu and Debian releases. Return the number added."""
    added = 0
    for os_name in ('ubuntu', 'debian'):
        order = release_order(os_name)
        supported = config['supported_versions'][os_name]
        unknown = [r for r in supported if r not in order]
        if unknown:
            sys.exit('error: unknown %s release %s' % (os_name, ', '.join(unknown)))
        os_arch = config['supported_arches'][os_name][0]

        def age(release):
            return order.index(release) if release in order else -1

        for codename in sorted(supported, key=age):
            older = [r for r in supported if age(r) < age(codename)]
            previous_release = max(older, key=age) if older else None
            added += add_release(config, rule_file, os_name, os_arch, codename,
                                 previous_release, age)
    return added


def add_release(config, rule_file, os_name, os_arch, codename, previous_release, age):
    """Add entries for one release to the rules missing it. Return the number added."""
    added = 0
    for key in sorted(rule_file.rules):
        rule = rule_file.rules[key]
        os_rule = rule.get(os_name) if isinstance(rule, dict) else None
        if not isinstance(os_rule, dict) or codename in os_rule:
            continue
        releases = [r for r in os_rule if r != '*']
        if not releases or any(k in os_rule for k in ('apt', 'pip', 'source')):
            continue
        # Only releases older than the missing one.
        releases = [r for r in releases if age(r) < age(codename)]
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
            print('%s: %s %s entry is not a package list, skipped' % (key, os_name, source))
            continue
        missing = [
            p for p in entry or []
            if not find_package(config, p, os_name, codename, os_arch)]
        if not entry or missing:
            fallback = "left to '*'" if has_star else 'not changed'
            if entry:
                print('%s: %s %s entry not available in %s (%s), %s' % (
                    key, os_name, source, codename, ', '.join(missing), fallback))
            else:
                print('%s: %s %s entry is empty, %s' % (key, os_name, source, fallback))
            continue

        rule_file.report('release-added', '%s: %s %s: [%s] (copied from %s)' % (
            key, os_name, codename, ', '.join(entry), source))
        position, indent = entry_position(rule_file, os_rule, codename)
        rule_file.insert(position, '%s%s: [%s]\n' % (indent, codename, ', '.join(entry)))
        # Newer releases may copy this entry.
        os_rule[codename] = entry
        added += 1
    return added


SIMPLE_UBUNTU_ENTRY = re.compile(r'^\s*ubuntu:\s*\[[^\]]*\]\s*(#.*)?$')

# Packages index URL -> names provided (Provides:) by the packages read from it
PROVIDES = {}
# codename -> names of the packages in, or provided by, an Ubuntu release
UBUNTU_NAMES = {}
# (codename, arch) -> names of the packages in, or provided by, an Ubuntu ports release
UBUNTU_PORTS_NAMES = {}


def enumerate_blocks_recording_provides(url, enumerate_blocks=deb.enumerate_blocks):
    """Enumerate the blocks of a package index like deb.enumerate_blocks, recording Provides."""
    provides = PROVIDES.setdefault(url, set())
    for block in enumerate_blocks(url):
        for name in block.get('Provides', '').split(','):
            # Drop any version, as in 'foo (= 1.0)'.
            if name.strip():
                provides.add(name.split()[0])
        yield block


def ubuntu_names(config, codename, os_arch):
    """Return the names of the packages in, or provided by, an Ubuntu release."""
    if codename not in UBUNTU_NAMES:
        names = set()
        for os_sources in config['package_sources']['ubuntu']:
            sources = os_sources.get(codename, []) if isinstance(os_sources, dict) else [os_sources]
            for source in sources:
                # Read the whole index, so all of its Provides are recorded.
                names.update(source.enumerate_packages('ubuntu', codename, os_arch))
        # Suites of the release are codename, codename-updates, ...
        for url, provides in PROVIDES.items():
            if '/dists/%s/' % codename in url or '/dists/%s-' % codename in url:
                names.update(provides)
        UBUNTU_NAMES[codename] = names
    return UBUNTU_NAMES[codename]


def read_index_names(url, use_artifacts, timeout):
    """
    Return the names of the packages in, or provided by, a Packages index.

    Return None if the index could not be read.
    """
    try:
        f = open_artifact_url(url, use_artifacts, timeout=timeout)
    except (OSError, EOFError):
        return None
    print('Reading debian package metadata from ' + url)
    names = set()
    with f:
        for line in f:
            # Some old indices have descriptions that are not UTF-8.
            line = line.decode('utf-8', errors='replace')
            if line.startswith('Package:'):
                names.add(line.split()[1])
            elif line.startswith('Provides:'):
                # Drop any version, as in 'foo (= 1.0)'.
                names.update(name.split()[0] for name in line[9:].split(',') if name.strip())
    return names


def old_ubuntu_names(codename, os_arch, use_artifacts):
    """
    Return the names of the packages in, or provided by, an old Ubuntu release.

    Only the release pocket is read, not -updates or -security. Return None
    if none of its package indices could be read.
    """
    if codename not in UBUNTU_NAMES:
        names = None
        for comp in OLD_UBUNTU_COMPONENTS:
            for mirror in OLD_UBUNTU_MIRRORS:
                url = '%s/dists/%s/%s/binary-%s/Packages.gz' % (mirror, codename, comp, os_arch)
                comp_names = read_index_names(url, use_artifacts, OLD_DOWNLOAD_TIMEOUT)
                if comp_names is not None:
                    names = (names or set()) | comp_names
                    break
            else:
                print('warning: could not read ubuntu %s %s' % (codename, comp), file=sys.stderr)
        UBUNTU_NAMES[codename] = names
    return UBUNTU_NAMES[codename]


def ports_ubuntu_names(codename, arch, use_artifacts):
    """
    Return the names of the packages in, or provided by, an Ubuntu release on a ports architecture.

    Return None if any of its package indices could not be read.
    """
    if (codename, arch) not in UBUNTU_PORTS_NAMES:
        urls = [
            '%s/dists/%s/%s/binary-%s/Packages.gz' % (UBUNTU_PORTS_MIRROR, suite, comp, arch)
            for suite in (codename, codename + '-updates', codename + '-security')
            for comp in OLD_UBUNTU_COMPONENTS]
        urls.append('%s/dists/%s/main/binary-%s/Packages.gz' % (ROS_BOOTSTRAP, codename, arch))
        names = set()
        for url in urls:
            url_names = read_index_names(url, use_artifacts, OLD_DOWNLOAD_TIMEOUT)
            if url_names is None:
                print('warning: could not read %s' % url, file=sys.stderr)
                names = None
                break
            names |= url_names
        UBUNTU_PORTS_NAMES[(codename, arch)] = names
    return UBUNTU_PORTS_NAMES[(codename, arch)]


def last_ubuntu_release(entry, first, os_arch, use_artifacts):
    """
    Find the newest Ubuntu release older than first that has all of the packages of entry.

    Return (release or None, releases newer than it that could not be read).
    """
    order = release_order('ubuntu')
    unread = []
    for codename in reversed(order[:order.index(first)]):
        names = old_ubuntu_names(codename, os_arch, use_artifacts)
        if names is None:
            unread.append(codename)
        elif all(p in names for p in entry):
            return codename, unread
    return None, unread


def current_ubuntu_releases(config, first):
    """Return the LTS and supported Ubuntu releases from first to the newest supported one."""
    rows = distro_info('ubuntu')
    order = [row['series'] for row in rows]
    supported = config['supported_versions']['ubuntu']
    if first not in order:
        sys.exit('error: unknown ubuntu release %s' % first)
    last = max(order.index(r) for r in supported)
    return [
        row['series'] for row in rows[order.index(first):last + 1]
        if 'LTS' in row['version'] or row['series'] in supported]


def fix_ubuntu_simple(config, rule_file, args):
    """Remove one line ubuntu entries not available in any current release. Return the number removed."""
    releases = current_ubuntu_releases(config, args.ubuntu_first_current)
    os_arch = config['supported_arches']['ubuntu'][0]
    removed = 0
    for key in sorted(rule_file.rules):
        rule = rule_file.rules[key]
        if not isinstance(rule, dict) or 'ubuntu' not in rule:
            continue
        entry = rule['ubuntu']
        if not isinstance(entry, list) or not entry:
            continue
        ubuntu_key = next(k for k in rule if k == 'ubuntu')
        index = ubuntu_key.__line__ - 1
        if not SIMPLE_UBUNTU_ENTRY.match(rule_file.lines[index]):
            continue
        available = [
            r for r in releases
            if all(p in ubuntu_names(config, r, os_arch) for p in entry)]
        if available:
            continue
        # Keep entries that ROS users on other architectures can still install.
        ports_names = {
            (r, arch): ports_ubuntu_names(r, arch, args.use_artifacts)
            for arch in UBUNTU_PORTS_ARCHES for r in releases}
        unread = sorted({arch for (_, arch), names in ports_names.items() if names is None})
        if unread:
            print('%s: ubuntu: [%s] not available in %s..%s, %s not read, not changed' % (
                key, ', '.join(entry), releases[0], releases[-1], ', '.join(unread)))
            continue
        ports = [
            '%s %s' % (arch, r) for (r, arch), names in ports_names.items()
            if all(p in names for p in entry)]
        if ports:
            print('%s: ubuntu: [%s] not available in %s..%s, but is on %s, not changed' % (
                key, ', '.join(entry), releases[0], releases[-1], ', '.join(ports)))
            continue
        reason = 'not available in %s..%s' % (releases[0], releases[-1])
        if args.last_release:
            last, unread = last_ubuntu_release(entry, releases[0], os_arch, args.use_artifacts)
            reason += ', last in %s' % last if last else ', not found in older releases'
            if unread:
                reason += ' (%s not read)' % ', '.join(unread)
        if len(rule) == 1:
            # Remove the whole rule, from its key line through the ubuntu entry.
            rule_file.report('rule-removed', '%s: ubuntu: [%s] removed with the rule (only entry, %s)' % (
                key, ', '.join(entry), reason))
            for i in range(key.__line__ - 1, index + 1):
                rule_file.remove(i)
        else:
            rule_file.report('ubuntu-removed', '%s: ubuntu: [%s] removed (%s)' % (key, ', '.join(entry), reason))
            rule_file.remove(index)
        removed += 1
    return removed


FIXES = {
    'add-releases': fix_add_releases,
    'ubuntu-simple': fix_ubuntu_simple,
}

# Kinds of changes reported by fixes, in report order, with the line introducing them
CHANGE_KINDS = {
    'release-added':
        'Entries added for supported releases (add-releases). Each is copied from an older '
        'release of the rule, and all of its packages exist in the release it is added for:',
    'ubuntu-removed':
        "One line 'ubuntu' entries removed (ubuntu-simple), because no current Ubuntu release "
        'has all of their packages:',
    'rule-removed':
        "Keys removed entirely (ubuntu-simple), because their only entry was a one line 'ubuntu' "
        'entry that no current Ubuntu release has all of the packages of:',
}


def write_report(argv, args, rule_files):
    """Write the changes made to rule_files, grouped by kind, to FIXES_REPORT."""
    lines = [
        'autofix_rosdep report, %s\n' % time.strftime('%Y-%m-%d %H:%M'),
        '\n',
        'Command: %s\n' % shlex.join([sys.argv[0]] + argv),
        '\n',
        'Dry run, the files were not changed.\n' if args.dry_run else
        'The files with changes were updated.\n',
    ]
    for rule_file in rule_files:
        lines.append('\n%s: %d changes\n' % (os.path.relpath(rule_file.path), len(rule_file.changes)))
        for kind, description in CHANGE_KINDS.items():
            texts = [text for k, text in rule_file.changes if k == kind]
            if texts:
                lines.append('\n  %s\n\n' % description)
                lines.extend('    %s\n' % text for text in texts)
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    with open(FIXES_REPORT, 'w') as f:
        f.writelines(lines)


def main(argv=sys.argv[1:]):
    config = load_config()
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        'files', nargs='+',
        help='rosdep files to fix, e.g. rosdep/base.yaml')
    parser.add_argument(
        '--fix', action='append', choices=sorted(FIXES),
        help='fix to apply, may be repeated (default: all)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='only show the changes that would be made')
    parser.add_argument(
        '--ubuntu-first-current', default='bionic', metavar='CODENAME',
        help='oldest Ubuntu release the ubuntu-simple fix checks (default: %(default)s)')
    parser.add_argument(
        '--last-release', action='store_true',
        help='with ubuntu-simple, report the last older Ubuntu release that had each removed '
             'entry (slow the first time, older indices are downloaded)')
    parser.add_argument(
        '--use-artifacts', action='store_true',
        help='use the package indices saved in %s instead of downloading them, '
             'downloading only those not saved yet' % os.path.relpath(ARTIFACTS_DIR))
    args = parser.parse_args(argv)

    # The Ubuntu and Debian sources read their package indices with deb.open_gz_url.
    deb.open_gz_url = lambda url: open_artifact_url(url, args.use_artifacts)
    # deb.enumerate_deb_packages reads its blocks with deb.enumerate_blocks.
    deb.enumerate_blocks = enumerate_blocks_recording_provides

    rule_files = []
    for path in args.files:
        rule_file = RuleFile(path)
        rule_files.append(rule_file)
        changes = 0
        for name in args.fix or sorted(FIXES):
            print("Applying fix '%s' to %s" % (name, os.path.relpath(path)))
            changes += FIXES[name](config, rule_file, args)
        sys.stdout.flush()
        print('%s: %d changes' % (os.path.relpath(path), changes), file=sys.stderr)
        if changes and not args.dry_run:
            rule_file.write()
            print('updated %s' % os.path.relpath(path), file=sys.stderr)

    write_report(argv, args, rule_files)
    print('changes listed in %s' % os.path.relpath(FIXES_REPORT), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
