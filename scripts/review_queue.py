#!/usr/bin/env python3

"""Triage the open ros/rosdistro pull request queue.

Read-only. Fetches every open pull request with its labels, changed paths, review
states and check rollup, sorts them into the REVIEW_GUIDELINES categories, and reports
what is blocking each one.

Requires the GitHub CLI (``gh``) to be installed and authenticated.
"""

import argparse
import json
import subprocess
import sys


REPO = 'ros/rosdistro'
BOT = 'github-actions'
PAGE_SIZE = 20
RETRIES = 3

# Deliberately small. Asking for ~100 pull requests with files and reviews in one
# request returns HTTP 502 from the GraphQL endpoint; paging at 20 is stable.
QUERY = """
query($cursor: String) {
  repository(owner: "ros", name: "rosdistro") {
    pullRequests(states: OPEN, first: %d, after: $cursor,
                 orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        isDraft
        mergeable
        mergeStateStatus
        updatedAt
        headRefOid
        author { login }
        labels(first: 15) { nodes { name } }
        files(first: 20) { nodes { path additions deletions } }
        reviews(first: 20) { nodes { author { login } state } }
        commits(last: 1) { nodes { commit { statusCheckRollup { state } } } }
      }
    }
  }
}
""" % PAGE_SIZE


def gh(args):
    """Run a gh command, retrying transient failures, and return stdout."""
    last = None
    for attempt in range(RETRIES):
        proc = subprocess.run(
            ['gh'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        if proc.returncode == 0:
            return proc.stdout
        last = proc.stderr.strip()
    raise RuntimeError('gh %s failed: %s' % (' '.join(args[:2]), last))


def fetch_pull_requests():
    """Page through every open pull request."""
    cursor = None
    nodes = []
    while True:
        args = ['api', 'graphql', '-f', 'query=' + QUERY]
        if cursor is not None:
            args += ['-F', 'cursor=' + cursor]
        page = json.loads(gh(args))['data']['repository']['pullRequests']
        nodes.extend(page['nodes'])
        if not page['pageInfo']['hasNextPage']:
            return nodes
        cursor = page['pageInfo']['endCursor']


def fetch_gated_runs():
    """Map head SHA to workflow run id for runs awaiting maintainer approval.

    A first-time contributor's `Validate rosdistro` run sits in `action_required`
    until a maintainer approves it, which leaves the pull request's required checks
    missing and its merge state BLOCKED.
    """
    raw = gh(['api', 'repos/%s/actions/runs?status=action_required&per_page=100' % REPO])
    runs = {}
    for run in json.loads(raw).get('workflow_runs', []):
        runs.setdefault(run['head_sha'], run['id'])
    return runs


def last_review_per_author(reviews):
    """Latest review state for each author, newest wins.

    GitHub lets an author's newer review supersede their older one, so a stale
    CHANGES_REQUESTED that the author has since replaced with an APPROVED must not
    count against the pull request.
    """
    latest = {}
    for review in reviews:
        author = (review.get('author') or {}).get('login')
        if author and review['state'] != 'PENDING':
            latest[author] = review['state']
    return latest


def categorize(files):
    """Sort a pull request by what it changes.

    The bump/entry/removal split is a heuristic on the diff size; confirm an
    individual pull request with `gh pr diff`.
    """
    paths = [f['path'] for f in files]
    distro = [f for f in files if f['path'].endswith('/distribution.yaml')]
    rosdep = [p for p in paths if p.startswith('rosdep/')]

    if rosdep and not distro:
        return 'rosdep'
    if not distro:
        return 'code' if paths else 'unknown'
    if rosdep:
        return 'mixed'

    additions = sum(f['additions'] for f in distro)
    deletions = sum(f['deletions'] for f in distro)
    if additions == 0 and deletions > 0:
        return 'removal'
    # A bump touches one distribution and rewrites the version line, sometimes
    # alongside the REP-143 header comment on line 3.
    if len(distro) == 1 and additions <= 2 and deletions <= 2:
        return 'bump'
    return 'entry'


def blockers_for(pr, gated_runs):
    """Everything standing between this pull request and a merge."""
    found = []
    labels = [label['name'] for label in pr['labels']['nodes']]
    reviews = last_review_per_author(pr['reviews']['nodes'])

    if pr['isDraft']:
        found.append('draft')
    if 'end-of-life' in labels:
        found.append('touches EOL distro')
    if pr['mergeable'] == 'CONFLICTING':
        found.append('conflicting')

    if pr['headRefOid'] in gated_runs:
        found.append('CI gated (run %d needs approval)' % gated_runs[pr['headRefOid']])
    else:
        commits = pr['commits']['nodes']
        rollup = commits[0]['commit']['statusCheckRollup'] if commits else None
        state = rollup['state'] if rollup else None
        if state in ('FAILURE', 'ERROR'):
            found.append('checks failing')
        elif state == 'PENDING':
            found.append('checks pending')
        elif state is None:
            found.append('no checks reported')

    humans = [a for a, s in reviews.items() if a != BOT and s == 'CHANGES_REQUESTED']
    if humans:
        found.append('changes requested by %s' % ', '.join(sorted(humans)))
    if reviews.get(BOT) == 'CHANGES_REQUESTED':
        found.append('bot requested changes')

    return found


def describe(pr, gated_runs):
    labels = [label['name'] for label in pr['labels']['nodes']]
    reviews = last_review_per_author(pr['reviews']['nodes'])
    approvals = sorted(a for a, s in reviews.items() if s == 'APPROVED' and a != BOT)
    return {
        'number': pr['number'],
        'title': pr['title'],
        'author': (pr['author'] or {}).get('login', '?'),
        'updated': pr['updatedAt'][:10],
        'category': categorize(pr['files']['nodes']),
        'labels': labels,
        'bot_review': reviews.get(BOT, '-'),
        'approvals': approvals,
        'blockers': blockers_for(pr, gated_runs),
        'url': 'https://github.com/%s/pull/%d' % (REPO, pr['number']),
    }


ORDER = ['bump', 'entry', 'removal', 'rosdep', 'mixed', 'code', 'unknown']

HEADINGS = {
    'bump': 'Version bumps (REVIEW_GUIDELINES type 1)',
    'entry': 'New or changed entries (type 2) - see REVIEW_PROCEDURE.md',
    'removal': 'Removals (type 4)',
    'rosdep': 'rosdep rules (type 3) - see REVIEW_PROCEDURE.md',
    'mixed': 'Mixed rosdep and distribution changes - split these',
    'code': 'Code and miscellaneous (types 5 and 6)',
    'unknown': 'No files reported',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--json', action='store_true',
                        help='emit the triage as JSON instead of a report')
    parser.add_argument('--category', choices=ORDER,
                        help='restrict the report to one category')
    parser.add_argument('--ready', action='store_true',
                        help='only show pull requests with no blockers')
    args = parser.parse_args()

    gated_runs = fetch_gated_runs()
    rows = [describe(pr, gated_runs) for pr in fetch_pull_requests()]

    total = len(rows)
    if args.category:
        rows = [r for r in rows if r['category'] == args.category]
    if args.ready:
        rows = [r for r in rows if not r['blockers']]

    if args.json:
        json.dump(rows, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write('\n')
        return 0

    if len(rows) == total:
        print('%d open pull requests\n' % total)
    else:
        print('%d of %d open pull requests after filtering\n' % (len(rows), total))
    for category in ORDER:
        group = sorted((r for r in rows if r['category'] == category),
                       key=lambda r: r['number'])
        if not group:
            continue
        print('== %s (%d)' % (HEADINGS[category], len(group)))
        for row in group:
            flags = []
            if row['bot_review'] not in ('APPROVED', '-'):
                flags.append('bot=%s' % row['bot_review'])
            if row['approvals']:
                flags.append('approved by %s' % ', '.join(row['approvals']))
            print('  #%-6d %-18s %s' % (row['number'], row['author'], row['title'][:70]))
            if flags:
                print('          %s' % '; '.join(flags))
            if row['blockers']:
                print('          BLOCKED: %s' % '; '.join(row['blockers']))
        print('')

    ready = [r for r in rows if not r['blockers']]
    print('%d of %d have no blocker.' % (len(ready), len(rows)))
    print('Check for sync freezes before merging anything: see REVIEW_PROCEDURE.md')
    return 0


if __name__ == '__main__':
    sys.exit(main())
