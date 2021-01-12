
This repository acts as an index for the ROS distributions.
If you would like to add a package to the index you can either index it for just documentation, for binary builds or continuous integration tests. 
This repository also holds the rosdep rules. 

Binary Releases
---------------

If you would like to add a package for binary release please see the [Bloom documentation](http://wiki.ros.org/bloom).
Bloom is a tool which will help you do the release as well as open a pull-request for you.
It will also assist adding documentation and source entries.
There are [several helpful tutorials](http://wiki.ros.org/bloom/Tutorials) which provide instructions on how to do things like [make a first release](http://wiki.ros.org/bloom/Tutorials/FirstTimeRelease). 

### Guidelines for Package Naming

When releasing a new package into a distribution, please follow the naming guidelines set out in the [ROS REP 144: ROS Package Naming](https://www.ros.org/reps/rep-0144.html).

### Binary Release Follow-up

Once a `ros/rosdisto` pull request is merged, the package will be built in the ROS build farm.
It is important that the author follow up to verify that the package has successfully built for a particular distribution.
This can be checked via both the distribution status page:
* For a ROS Distribution, use `repositories.ros.org/status_page/`, for example [ROS packages for Melodic](http://repositories.ros.org/status_page/ros_melodic_default.html).
* For a ROS 2 Distribution, use `repo.ros2.org/status_page/`, for example [ROS packages for Foxy](http://repo.ros2.org/status_page/ros_foxy_default.html).

Additionally, it may be necessary to determine build failures, these jobs are located at:
* [ROS 2 Buildfarm](http://build.ros2.org/)
* [ROS Buildfarm](http://build.ros.org/)

If a package continuously fails to build, the ROS Boss for that distribution may choose to revert the pull request that introduced it.
Or they may take [other actions](https://github.com/ros-infrastructure/ros_buildfarm/blob/master/doc/ongoing_operations.rst) to avoid repeated failures.

Documentation Indexing
----------------------

If you just want to submit for documentation indexing only [this tutorial](http://wiki.ros.org/rosdistro/Tutorials/Indexing%20Your%20ROS%20Repository%20for%20Documentation%20Generation) will get you going. 

Continuous Integration Indexing
-------------------------------

If you would like to index your package for continuous integration tests you can add a source entry in the same way as the documentation index.

The `version` field is required to be a branch name. This is due to the Jenkins Git Plugin that will always trigger if a repository has changed. After querying Cloudbees support they replied with:

> The git plugin is configured to build for a tag / sha1 will always trigger a build.

As such the CI on this repository will enforce that the source version is a branch to not cause continuous triggering of builds.
Also of note is that a tag has priority over a branch with the same name so a tag with the same name as the branch cannot exist either.


rosdep rules contributions
--------------------------

This repository also holds the rosdep keys.
There is a guide for submitting rosdep keys [here](http://docs.ros.org/independent/api/rosdep/html/contributing_rules.html).
Updates to rosdep rules require the review of two people.
This will usually means that it needs a +1, and then it can be merged by a different person.

For convenience in reviewing, please comment in the PR with links to the web listings of packages such as on http://packages.ubuntu.com, http://packages.debian.org, and https://apps.fedoraproject.org/packages or if a pip package pypi.python.org.

Please also briefly describe the package being added and what use case you want to use it for.
It's valuable to have a record of the packages as submitted and their intended purpose for clarity in the future so that if there's a conflict there's information to fall back on instead of speculation about the original use cases.

Guidelines for rosdep rules
---------------------------

 * Native packages are strongly preferred. (They are required for packaging and have upgrade and conflict tracking.)
 * Please use the smallest notation possible.
   For example if an ubuntu package is the same for all versions only write the generic ubuntu rule, don't call out the same package name for every version of ubuntu.
   Similarly don't call out indirect dependencies or default options for packages.
 * Python packages should go in the `python.yaml`.
 * Homebrew into `osx-homebrew.yaml`.
 * Supported Platforms
   * Rules can be contributed for any platform.
     However to be released they must be at least cover the supported platforms in REP 3: http://www.ros.org/reps/rep-0003.html So:
    * Ubuntu and Debian are top priority.
    * Fedora and Gentoo have packaging jobs and should be filled in if they are available.
    * OSX is also nice to have.
    * If specific versions are called out, there should be coverage of all versions currently targeted by supported ROS distros.
     * If there's a new distro in prerelease adding a rule for it is fine.
       However please don't target 'sid' as it's a rolling target and when the keys change our database gets out of date.
  * Keep everything in alphabetical order for better merging.
  * No trailing whitespace.
  * No blank lines.

### Expected Rosdep Sources

Keys in the rosdep database are required to come from packages contained in the following repositories only.

#### Ubuntu

* Ubuntu Repositories: Main, Universe, or Multiverse
* ROS Sources: https://wiki.ros.org/Installation/Ubuntu/Sources

#### Debian

* Debian Repositories: Main, Contrib, or Non-Free
* ROS Sources: The Ubuntu guide also works for currently supported Debian distributions: https://wiki.ros.org/Installation/Ubuntu/Sources

#### Fedora

* Fedora Project Repositories: release or updates

#### RHEL/CentOS

* CentOS Repositories: base, extras, centos-sclo-rh, or updates
  * Additionally, for CentOS 8+: AppStream or PowerTools
* Fedora Project Repositories: epel

#### MacOS

TODO

#### Gentoo

* Gentoo Portage Repository (e.g. `rsync://rsync.us.gentoo.org/gentoo-portage`)
* ROS-Overlay: `https://github.com/ros/ros-overlay`

If the ebuild you are referencing is not in either of those locations, please
file a PR into ROS-Overlay to add it and any needed dependencies to the tree.

#### Arch Linux

Packages must be in the official Archlinux core, extra, or community repositories at the time they are contributed.

Packages in the AUR may not be added directly.
Work has been proposed to add a separate installer for AUR packages [ros-infrastructure/rosdep#560](https://github.com/ros-infrastructure/rosdep/issues/560).

#### Alpine Linux

* Alpine Linux requires the [`edge`](https://wiki.alpinelinux.org/wiki/Edge#Upgrading_to_Edge) release and [`testing`](https://wiki.alpinelinux.org/wiki/Aports_tree#testing) aports branch.

#### FreeBSD

* FreeBSD project pkg repository: main or quarterly
* A database of FreeBSD packages is available at https://freshports.org

#### pip

For pip installers they are expected to be in the main PyPI index https://pypi.org/.

### Python rules

#### Python 3

When adding rules for python 3 packages, create a separate entry prefixed with `python3-` rather than `python`
For example:

```yaml
python-foobar:
  debian: [python-foobar]
  fedora: [python2-foobar]
  ubuntu: [python-foobar]
...
python3-foobar:
  debian: [python3-foobar]
  fedora: [python3-foobar]
  ubuntu: [python3-foobar]
```

You may see existing rules that use `_python3`-suffixed distribution codenames.
These were trialed as a possible style of Python 3 rules and should not be used.
`_python3`-suffixed keys may be removed when the platform they're targeting reaches end of life.
The guidance above should be followed for new rules.
Additionally, if you rely on a dependency that uses `_python3`-suffixed codenames, add a new rule for it that follows the guidance above.

#### pip

Python packages, which are only available on [PyPI](https://pypi.org/), should use the prefix `python3-` and suffix `-pip` to avoid colliding with future keys from package managers.

For example:

```yaml
python3-foobar-pip:
  ubuntu:
    pip:
      packages: [foobar]
```

Some existing rules do not have `python-` or `python3-` prefixes, but this is no longer recommended.
If the package ever becomes available in Debian or Ubuntu, the `python3-` prefix ensures that the `pip` key is next to it alphabetically.
The `-pip` key should be removed when the package becomes available on all platforms, and all existing users of the `-pip` key should migrate to the new key.

How to submit pull requests
---------------------------

When submitting pull requests it is expected that they pass the unit tests for formatting. 
The unit tests enforce alphabetization of elements and a consistent formatting to keep merging as clean as possible. 

To run the tests run ``nosetests`` in the root of the repository.
These tests require several dependencies that can be installed either from the ROS repositories or via pip(list built based on the content of [.travis.yaml](https://github.com/ros/rosdistro/blob/master/.travis.yml):

|   Dependency   |            Ubuntu package         |   Pip package  |
| :------------: | --------------------------------- | -------------- |
| catkin_pkg     | python-catkin-pkg                 | catkin-pkg     |
| github         | python-github                     | PyGithub       |
| nose           | python-nose                       | nose           |
| rosdistro      | python-rosdistro                  | rosdistro      |
| ros_buildfarm  | python-ros-buildfarm              | ros-buildfarm  |
| unidiff        | python-unidiff (Zesty and higher) | unidiff        |
| yamllint       | yamllint                          | yamllint       |

There is a tool ``rosdistro_reformat`` which will fix most formatting errors such as alphabetization and correct formatting.

Note: There's a [known issue](https://github.com/disqus/nose-unittest/issues/2) discovered [here](https://github.com/ros/rosdistro/issues/16336) that most tests won't run if you have the python package `nose-unitttest` installed. 
