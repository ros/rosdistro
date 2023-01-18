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

## Adding new repository checks

Platform checks can be added by updating [config.yaml](./config.yaml).

* `package_sources` contains a set of repository base urls for each operating system distribution
* `package_dashboards` contains an optional list of matching repository url patterns and template urls which can be used to extract and compose web links to packages in the matching distributions. This configuration is optional and may be omitted where appropriate.
* `supported_versions` lists of operating system versions or codenames to run package presence checks for. The last version listed will be used to generate suggestions if there is no definition for that operating system.
* `supported_architectures` lists of operating system architectures to run package presence checks for. Although rosdep is expected to work across architectures repositories are only checked on amd64/x86_64 to save time. If a distribution has a radically different set of packages for different architectures checks for additional architectures can be added.
