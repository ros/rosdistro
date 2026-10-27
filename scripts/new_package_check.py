#!/usr/bin/env python3

"""Gather the new-package review checklist for a source repository.

Read-only, over the GitHub API, so there is nothing to clone. Reports repository
visibility and fork status, every LICENSE-like file, and for each package.xml its
name, declared licenses, and whether the name satisfies REP-144.

The OSI-approval and fork judgments are left to the reviewer; see
REVIEW_PROCEDURE.md.

Requires the GitHub CLI (``gh``) to be installed and authenticated.
"""

import argparse
import base64
import json
import re
import subprocess
import sys


# REP-144: lowercase, starts with a letter, letters/digits/underscores only.
REP144 = re.compile(r'^[a-z][a-z0-9_]*$')
LICENSE_FILE = re.compile(r'(^|/)(LICENSE|LICENCE|COPYING)([.-][^/]*)?$', re.IGNORECASE)
NAME = re.compile(r'<name>\s*([^<]*)</name>')
LICENSE_TAG = re.compile(r'<license[^>]*>\s*([^<]*)</license>')
RETRIES = 3


def gh_json(path):
    """GET a GitHub API path and parse the response, retrying transient failures."""
    last = None
    for attempt in range(RETRIES):
        proc = subprocess.run(
            ['gh', 'api', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        last = proc.stderr.strip()
    raise RuntimeError('gh api %s failed: %s' % (path, last))


def read_manifest(repo, path, ref):
    """Fetch one package.xml and pull out its name and license tags."""
    blob = gh_json('repos/%s/contents/%s?ref=%s' % (repo, path, ref))
    text = base64.b64decode(blob['content']).decode('utf-8', 'replace')
    name = NAME.search(text)
    return {
        'path': path,
        'name': name.group(1).strip() if name else None,
        'licenses': [m.group(1).strip() for m in LICENSE_TAG.finditer(text)],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('repo', help='source repository as owner/name')
    parser.add_argument('ref', nargs='?',
                        help='branch or tag to inspect (default: the default branch)')
    parser.add_argument('--max-manifests', type=int, default=40,
                        help='stop after this many package.xml files (default: 40)')
    args = parser.parse_args()

    repo = gh_json('repos/%s' % args.repo)
    ref = args.ref or repo['default_branch']

    print('%s @ %s' % (args.repo, ref))
    print('  public:   %s' % (not repo['private']))
    print('  archived: %s' % repo['archived'])
    if repo['fork']:
        parent = (repo.get('parent') or {}).get('full_name', 'unknown')
        print('  FORK of %s - needs a reason; see REVIEW_PROCEDURE.md' % parent)
    print('  GitHub-detected license: %s'
          % ((repo.get('license') or {}).get('spdx_id') or 'none'))

    tree = gh_json('repos/%s/git/trees/%s?recursive=1' % (args.repo, ref))
    if tree.get('truncated'):
        print('\n  WARNING: tree listing truncated; clone to check this one properly')
    paths = [e['path'] for e in tree.get('tree', []) if e['type'] == 'blob']

    licenses = [p for p in paths if LICENSE_FILE.search(p)]
    print('\n  LICENSE files: %s' % (', '.join(licenses) if licenses else 'NONE FOUND'))

    manifests = [p for p in paths if p == 'package.xml' or p.endswith('/package.xml')]
    print('  package.xml:   %d' % len(manifests))
    if not manifests:
        print('    No ROS packages found. Accepted only rarely, with special handling')
        print('    in the release repository.')
        return 0

    declared = set()
    problems = []
    for path in manifests[:args.max_manifests]:
        pkg = read_manifest(args.repo, path, ref)
        flags = []
        if not pkg['name']:
            flags.append('NO <name>')
        elif not REP144.match(pkg['name']):
            flags.append('REP-144 VIOLATION')
        if not pkg['licenses']:
            flags.append('NO <license>')
        declared.update(pkg['licenses'])
        print('    %-50s %-28s %s'
              % (path, pkg['name'] or '?',
                 ' | '.join(pkg['licenses']) or '-'))
        if flags:
            problems.append((path, flags))
            print('      %s' % '; '.join(flags))

    if len(manifests) > args.max_manifests:
        print('    ... %d more not read (--max-manifests)'
              % (len(manifests) - args.max_manifests))

    print('\n  Distinct licenses declared: %s'
          % (', '.join(sorted(declared)) if declared else 'NONE'))
    print('\nChecklist:')
    print('  [%s] LICENSE file present' % ('x' if licenses else ' '))
    print('  [%s] every package.xml declares a license'
          % (' ' if any('NO <license>' in f for _, f in problems) else 'x'))
    print('  [%s] names satisfy REP-144'
          % (' ' if any('REP-144 VIOLATION' in f for _, f in problems) else 'x'))
    print('  [%s] source repository is public' % ('x' if not repo['private'] else ' '))
    print('  [%s] contains ROS packages' % ('x' if manifests else ' '))
    print('  [ ] license is OSI-approved (judge from the list above)')
    print('  [ ] not an unexplained fork')
    return 0


if __name__ == '__main__':
    sys.exit(main())
