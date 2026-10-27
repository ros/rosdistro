# Notes for automated assistants

This repository is the index of packages released into each ROS distribution, plus the
rosdep database. Almost every change is data, not code, and almost every change is
reviewed by a maintainer before it merges.

Read first:

* [CONTRIBUTING.md](CONTRIBUTING.md) — what a contribution has to look like.
* [REVIEW_GUIDELINES.md](REVIEW_GUIDELINES.md) — the categories of pull request and what
  a reviewer must confirm for each.
* [REVIEW_PROCEDURE.md](REVIEW_PROCEDURE.md) — how to work the queue, which signals mean
  what, and which checks nothing automated performs.

## Rules

These constrain an assistant working on this repository. They are not claims about how
any individual maintainer reviews.

* **Evidence is not a review.** You can gather every item on the new-package checklist
  and still not have reviewed anything. A maintainer decides.
* **Never merge a new package or a new distribution entry.** That means any new or
  changed `release`, `source`, or `doc` entry, including a package already released in
  another distribution arriving in a new one, and including source-only additions.
  Present the completed checklist and stop.
* **Post the completed checklist on the pull request.** The record of why a package was
  accepted belongs on the pull request, not in a transcript. A bare approval is right for
  a version bump and wrong for a new package. Ask the maintainer before posting anything
  under their name.
* **Do not approve, request changes, comment, or reply to a review thread** unless asked
  for that specific act. Draft the wording and hand it over.
* **No assistant attribution in review bodies, approvals, or merge commits.** A review
  reads as the work of whoever signed it.
* **Confirm a batch before running it.** Working through many version bumps in one pass
  is normal; confirm the list first, then use the guards in
  [REVIEW_PROCEDURE.md](REVIEW_PROCEDURE.md#acting-on-many-at-once).
* **Say what you could not verify.** A report claiming the checklist passed when one item
  was unreachable is worse than one that names the gap.

## Tools

Both are read-only and need the [GitHub CLI](https://cli.github.com/):

```
scripts/review_queue.py              # triage every open pull request, with blockers
scripts/new_package_check.py REPO    # new-package checklist, without cloning
```

## Tests

`pytest -s test` and `yamllint .`, as in `.github/workflows/build_test.yaml`. Anything
touching `rosdep/` is also checked against real package repositories by
`test/rosdep_repo_check`, but only on the platforms in its `config.yaml`.
