rosdistro Review Procedure
==========================

[REVIEW_GUIDELINES.md](REVIEW_GUIDELINES.md) is the policy: the categories of pull request
and what a reviewer must confirm for each. This document is the procedure that goes with
it — how to work the open queue, which signals mean what they appear to mean, and which
parts of the policy nothing automated checks. Where the two disagree, the policy wins and
this document needs fixing.

Sync freezes
------------

Every distribution syncs on its own schedule, so this is always a per-distribution
question, and it decides the whole version-bump pile. Establish it before triaging.

Find the newest `Preparing for <Distro> sync` topic in the
[release category](https://discourse.ros.org/c/release/16) and read to the end: the freeze
is over once a later post in that topic says the sync is out. The category and topics are
also available as JSON, at `/c/ros/release/16.json?order=created` and `/t/<id>.json` on
`discourse.openrobotics.org`, which is quicker than opening five topics in a browser.

Two traps: the announced date is a plan and syncs slip by days, so a topic whose last post
says "running a little behind" is still a freeze; and the `held for sync` label is not
state, because it often outlives the freeze by weeks. Read the topic, not the label.
Rolling has no regular cadence.

During a freeze, REVIEW_GUIDELINES says to approve the bump with a "Holding for sync
freeze" note linking the topic, then merge once the sync is out.

Working the queue
-----------------

`scripts/review_queue.py` does the fetching and sorting. By hand:

* `gh pr list --json number,title,files,reviews,...` with a limit near 100 returns
  HTTP 502 from the GraphQL endpoint. Paging GraphQL at 20 nodes with `files(first: 20)`
  and `reviews(first: 20)` is stable; retry each page, since 502s here are transient.
* `gh api repos/ros/rosdistro/pulls --paginate` is the dependable fallback, but carries no
  reviews or checks.
* Per pull request, `gh pr view <n> --json state,mergeable,statusCheckRollup,reviews,files`,
  plus `gh pr diff <n>` and `gh pr checks <n>`.

Sort by what the diff touches: a `version:` under an existing entry is a version bump; a
new or changed `release`/`source`/`doc` entry is a new entry; `rosdep/*.yaml` is a rosdep
rule; a removed entry is a removal. An end-of-life distribution's `distribution.yaml` is
sealed, which is what the `end-of-life` label and the rule in `.github/mergify.yml` are
for.

### Blockers

| State | Meaning |
| --- | --- |
| `BLOCKED`, only `Generate automated review` and `triage` reported | `Validate rosdistro` is in `action_required` behind the first-time-contributor gate |
| Every check green, merge refused as "base branch policy prohibits the merge" | The reported check names no longer match the required contexts — see below |
| A check failing | Read the log. Many are real and mechanical, such as a source URL missing its `.git` suffix failing `test_rosdistro_urls`. Some are infrastructure, such as a runner TLS failure in `git fetch`, and want a re-run |
| `CONFLICTING` | Needs a rebase or `gh pr update-branch` |
| Human `CHANGES_REQUESTED` | Waiting on the contributor; do not re-litigate another reviewer's request |
| Bot `CHANGES_REQUESTED` with a later bot `APPROVED` | Already resolved — see below |
| Draft | The automated reviewer does not review drafts |
| `mergeable: UNKNOWN` | GitHub is recomputing after a merge. Not a blocker |

To open the first-time-contributor gate, list the waiting runs and approve the one whose
`head_sha` matches the pull request's `headRefOid`, so you do not approve a stale run:

```
gh api "repos/ros/rosdistro/actions/runs?status=action_required&per_page=100" --jq '.workflow_runs[] | "\(.id) \(.head_sha) \(.head_branch)"'
gh api -X POST "repos/ros/rosdistro/actions/runs/<id>/approve"
```

**Required check names must match exactly.** Branch protection requires the contexts
`Yaml Linting` and `rosdistro / rosdep checks`. While `build_test.yaml` used a Python
matrix those jobs reported as `Yaml Linting (3.8)`, so any pull request whose CI last ran
before the matrix was removed still reports suffixed names. Those satisfy nothing, and the
pull request shows every check green while refusing to merge, with no explanation beyond
the base-branch-policy message. Compare the two:

```
gh api repos/ros/rosdistro/branches/master/protection --jq '.required_status_checks.contexts'
gh pr view <n> --json statusCheckRollup -q '[.statusCheckRollup[].name]'
```

`gh pr update-branch` gives the pull request a new head and fresh CI, which fixes it.

**A stale review is not a request.** Reviews are chronological and a newer review from an
author supersedes their older one, so a filter that skips any pull request with a
`CHANGES_REQUESTED` anywhere in the list will skip ones the author has since approved.
Compare the last review per author.

### Acting on many at once

Squash is the merge method here. Guard each merge on `state == OPEN`,
`mergeable != CONFLICTING`, no check with a failing conclusion, and no
`CHANGES_REQUESTED` in the last review of any human author.

Do not add `mergeStateStatus == CLEAN` to that list. Every merge moves master and GitHub
briefly reports `UNKNOWN` for every other open pull request while it recomputes; a
CLEAN-only guard once merged 1 of 8 and silently skipped the rest. The guard above is safe
because `gh pr merge` refuses a pull request that cannot be merged.

Re-read each pull request immediately before acting on it, since other maintainers are
working the same queue.

Line 3 of every `distribution.yaml` is the REP-143 comment, written by whichever version
of the `rosdistro` package the contributor has installed, so it flips between the old and
current URL from one pull request to the next. CI accepts both. It is noise.

Reading the automated reviewer
------------------------------

`ros-infrastructure/rosdistro-reviewer` posts as `github-actions`. The
`Generate automated review` check only reports that it ran; what it concluded is the
*state* of its review — APPROVED, COMMENTED or CHANGES_REQUESTED. Inside the body, ❌ is
blocking and 📝 is informational, so an out-of-date bloom version on an otherwise clean
bump is not disqualifying.

It examines new package and repository naming, release repository hosting org, bloom
version, whether release changes stay confined to one distribution, rosdep key naming,
rosdep platform validity, rosdep key suitability, and yamllint on added lines. That is the
whole vocabulary. Every review also carries a boilerplate preamble mentioning REP-144 and
OSI licenses; that text is not a finding.

**It never looks at licenses** — not LICENSE files, not OSI approval, not `<license>`
tags. A fully green review says nothing about any of them.

rosdep rules
------------

Policy is CONTRIBUTING.md under "rosdep rules contributions", "Guidelines for rosdep
rules", and "Expected Rosdep Sources".

Two people must review. If yours is the first approval, add the
`rosdep-needs-second-approval` label and request review from the other person on the
rotation. An approval only counts toward the two if the reviewer can merge here, so check
when relying on one — community reviews are valuable but are not the second approval:

```
gh api repos/ros/rosdistro/collaborators/<user>/permission --jq .permission
```

### What is machine-checked

`test/rosdep_repo_check` resolves the keys a pull request touches against real package
repositories, for exactly the platforms and versions listed in its `config.yaml` —
currently ubuntu, debian, fedora, rhel, opensuse, arch, alpine and openembedded. Re-read
that file rather than trusting this list. To check the whole database rather than one
diff, `PYTHONPATH=test python3 -m rosdep_repo_check`.

### What is not checked

**No check anywhere resolves package names on `gentoo`, `nixos`, `openeuler`, `osx`,
`freebsd` or `slackware`.** The automated reviewer validates that a platform name is
spelled correctly, never that a package exists, and neither does any test. Every wrong
name on those platforms reaches master unless a human catches it, and in practice that is
where the findings are.

* **Gentoo** — `https://packages.gentoo.org/packages/<category>/<name>.json`; 404 means no
  such package. Read the `description`, because a plausible name can be a different
  program: `dev-util/gperf` is the GNU perfect hash function generator, while gperftools
  is `dev-util/google-perftools`. When a package genuinely is not in Portage or
  ros-overlay, CONTRIBUTING.md prescribes the remedy — open an issue on
  [ros-overlay](https://github.com/ros/ros-overlay), omit the gentoo key, and link the
  issue. An invented ebuild name is worse than no key.
* **NixOS** — attribute names, which get renamed. Check `pkgs/top-level/aliases.nix` in
  nixpkgs for the rename and its date before accepting or rejecting one.
* **openEuler** — newer releases serve a JavaScript listing page, so use the repodata:
  read the `primary.xml.zst` href from `everything/x86_64/repodata/repomd.xml`, decompress
  it with `zstandard` (already a test dependency), and collect the `<name>` elements.
  Check each supported LTS line separately, since names differ between them.
* **Homebrew** — `https://formulae.brew.sh/api/formula/<name>.json`.

### Judgment

Native packages are required over pip: a package depending on a `pip` key cannot be
released into a distribution at all. Where pip is the only option the key is named
`python3-PACKAGENAME-pip`, and REVIEW_GUIDELINES has a disclaimer to post with the review.
Where a native package exists, the key name matches the Ubuntu binary package name.
Ubuntu and Debian are required; Fedora and Gentoo are expected where available, and a rule
covering only Debian and Ubuntu is acceptable.

Never rename an existing key — that breaks every package depending on it.

Check precedent before calling a value wrong. A `fedora:` entry naming a source package
(`python-foo`) where the binary is `python3-foo` looks like a bug, but it is the house
pattern in roughly eighty entries, including long-established ones. Count them with
`grep -cE "^  fedora: \[python-" rosdep/python.yaml` before asking a contributor to fix a
systemic inconsistency that predates their pull request.

Splitting a key is a behaviour change, not a cleanup. Moving the development package out
of a runtime key means anything that build-depends on the runtime key loses its headers at
the next rebuild.

### Removals

`test_rosdep_repo_check` finds the rules to validate by parsing the added line numbers of
`git diff --unified=0 <upstream master> -- rosdep`. Because `rosdep/*.yaml` is extremely
repetitive, deleting keys that are *interleaved* with keys you keep lets git find an
equally short edit script that re-aligns untouched keys as delete-plus-add pairs. Those
then look added, so the test treats them as new rules and fails resolving long-dead
packages, naming keys the diff never touched. Hunting the named keys goes nowhere; the
cause is the alignment. Remove the whole contiguous remainder instead, and verify that
only intended keys appear:

```
git diff --unified=0 origin/master -- rosdep | grep '^+' | sed 's/^+//' | grep -E '^[A-Za-z0-9_.+-]+:'
```

New packages and new entries
----------------------------

Any new or changed `release`, `source` or `doc` entry, including source-only and doc-only
additions. A pull request should touch a single distribution, because release changes in
two at once couple their syncs; source-only additions across several are routine.

**Already released in another distribution** (REVIEW_GUIDELINES case 2.1): the question is
URL consistency. The `doc`, `release` and `source` URLs must match what the package uses
elsewhere, which `grep -rn -A14 "^  <repo_key>:" */distribution.yaml` will show. Where they
differ, ask why and whether the original can be reused. A project that moved hosts is a
legitimate difference when the body explains it and the release repository is unchanged.

**Brand new to the ROS ecosystem**: the full checklist in REVIEW_GUIDELINES. Nothing
automated checks any of the license items. `scripts/new_package_check.py` gathers
everything except the OSI and fork judgments over the GitHub API, so no clone is needed; a
clone is only worth it when the tree listing truncates or the sources themselves matter.

Judging what comes back:

* `<license>Apache-2.0</license>` is unambiguous; `Apache License 2.0` or a bare `BSD` is
  not SPDX and is widespread in existing packages. The requirement is that the license is
  OSI-approved and reflected in every manifest, not that the string is SPDX.
* Public domain and CC-BY are free but not OSI-approved, which is a conversation. NC, ND
  and proprietary terms are a refusal, since the build farm cannot redistribute them.
* A vendor package that downloads a prebuilt artifact at build time is an established
  pattern, but the artifact carries its own license. Check that, not just the wrapper.
* A fork needs a reason. The submitter should have opened an issue upstream asking for a
  release and waited about four weeks. Check whether the upstream was released under a
  different repository key, because a fork arriving under the same key is a larger problem.
* For Rolling the release repository belongs in [ros2-gbp](https://github.com/ros2-gbp) so
  the package releases forward automatically into the next stable distribution; the
  automated reviewer enforces this. For a stable distribution, one under the maintainer's
  own account is acceptable.
* An entry with a `release` field should normally come from bloom. If it did not, ask why.

The completed checklist gets posted on the pull request. REVIEW_GUIDELINES keeps a
copy-pasteable template with collapsible sections for the package-name and license output,
because the record of why a package was accepted has to live on the pull request rather
than in a reviewer's head.
