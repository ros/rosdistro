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

  scripts/autofix_rosdep/autofix_rosdep.py --dry-run rosdep/base.yaml

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

Downloaded package indices are saved in the artifacts folder at the top of
the repository. If a download fails or times out, the saved copy from a
previous run is used instead, with a warning. --use-artifacts skips the
downloads.

This script was written by Opus 5.5 and not thoroughly tested. Use with caution.
"""

import argparse
import csv
import gzip
import io
import os
import sys
import time

import yaml

BASEDIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(BASEDIR, 'test'))

from rosdep_repo_check import deb  # noqa: E402
from rosdep_repo_check import find_package  # noqa: E402
from rosdep_repo_check import open_compressed_url  # noqa: E402
from rosdep_repo_check.config import load_config  # noqa: E402
from rosdep_repo_check.yaml import AnnotatedSafeLoader  # noqa: E402

ARTIFACTS_DIR = os.path.join(BASEDIR, 'artifacts')
DISTRO_INFO = '/usr/share/distro-info/%s.csv'
DOWNLOAD_TIMEOUT = 10


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

    def insert(self, index, text):
        self.insertions.append((index, text))

    def write(self):
        lines = list(self.lines)
        # Lines inserted at the same index end up in alphabetical order.
        for index, text in sorted(self.insertions, reverse=True):
            lines.insert(index, text)
        with open(self.path, 'w') as f:
            f.writelines(lines)


def artifact_path(url):
    """Return the path of the saved (gzip compressed) copy of a download."""
    name = url.split('://', 1)[1].replace('/', '_')
    if not name.endswith('.gz'):
        name += '.gz'
    return os.path.join(ARTIFACTS_DIR, name)


def open_artifact_url(url, use_artifacts):
    """
    Open a package index URL, saving a copy of it in the artifacts folder.

    If the download fails or times out, or use_artifacts is set, the copy
    saved by a previous run is used instead.
    """
    path = artifact_path(url)
    if not use_artifacts:
        try:
            with open_compressed_url(url, retry=0, timeout=DOWNLOAD_TIMEOUT) as f:
                data = f.read()
        except (OSError, EOFError) as e:
            if not os.path.exists(path):
                raise
            print('warning: could not download %s (%s), using the copy saved %s' % (
                url, e, time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(path)))),
                file=sys.stderr)
        else:
            os.makedirs(ARTIFACTS_DIR, exist_ok=True)
            with gzip.open(path + '.tmp', 'wb', compresslevel=1) as f:
                f.write(data)
            os.replace(path + '.tmp', path)
            return io.BytesIO(data)
    elif not os.path.exists(path):
        sys.exit('error: no saved copy of %s in %s' % (url, ARTIFACTS_DIR))
    return gzip.open(path, 'rb')


def release_order(os_name):
    """Return the codenames of an OS, oldest first, from distro-info."""
    path = DISTRO_INFO % os_name
    if not os.path.exists(path):
        sys.exit('error: %s is needed to order %s releases (install distro-info-data)' %
                 (path, os_name))
    with open(path) as f:
        return [row['series'] for row in csv.DictReader(f)]


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

        print('%s: %s %s: [%s] (copied from %s)' % (
            key, os_name, codename, ', '.join(entry), source))
        position, indent = entry_position(rule_file, os_rule, codename)
        rule_file.insert(position, '%s%s: [%s]\n' % (indent, codename, ', '.join(entry)))
        # Newer releases may copy this entry.
        os_rule[codename] = entry
        added += 1
    return added


FIXES = {
    'add-releases': fix_add_releases,
}


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
        '--use-artifacts', action='store_true',
        help='use the package indices saved in %s instead of downloading them' %
             os.path.relpath(ARTIFACTS_DIR))
    args = parser.parse_args(argv)

    # The Ubuntu and Debian sources read their package indices with deb.open_gz_url.
    deb.open_gz_url = lambda url: open_artifact_url(url, args.use_artifacts)

    for path in args.files:
        rule_file = RuleFile(path)
        changes = 0
        for name in args.fix or sorted(FIXES):
            print("Applying fix '%s' to %s" % (name, os.path.relpath(path)))
            changes += FIXES[name](config, rule_file, args)
        sys.stdout.flush()
        print('%s: %d changes' % (os.path.relpath(path), changes), file=sys.stderr)
        if changes and not args.dry_run:
            rule_file.write()
            print('updated %s' % os.path.relpath(path), file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
