 a system for checking rosdep rules against the current package repositories for supported platforms

## Running on rosdep PRs

This test package is configured to run during pull request checks on changed rosdep key entries.

If a package can't be found in the repositories, a failing test is registered notifying the contributor.
Links to package web indexes/dashboards is also printed in the action logs.


## Running locally on the entire rosdep database

To review the entire rosdep database and not only the rules that were changed in the most recent commit, it is also possible to invoke the test as a python module. For example:
```

PYTHONPATH=test python3 -m rosdep_repo_check
```
