
This repository acts as an index for the ROS distributions.
If you would like to add a package to the index you can either index it for just documentation, for binary builds or continuous integration tests.
This repository also holds the rosdep rules.

Binary Releases
---------------

If you would like to add a package for binary release please see the [Bloom documentation](http://wiki.ros.org/bloom).
Bloom is a tool which will help you do the release as well as open a pull-request for you.
It will also assist adding documentation and source entries.
There are [several helpful tutorials](http://wiki.ros.org/bloom/Tutorials) which provide instructions on how to do things like [make a first release](http://wiki.ros.org/bloom/Tutorials/FirstTimeRelease).

Once you have made a release make sure that you are subscribed to the appropriate subcategory of our [Release management Category](https://discourse.ros.org/c/release/16) for the appropriate distros.
This is our primary method of communications with maintainers and is where the ROS Boss will coordinate releases.
It is expected that all maintainers are watching those categories to allow us to coordinate.

### Guidelines for Package Naming

When releasing a new package into a distribution, please follow the naming guidelines set out in the [ROS REP 144: ROS Package Naming](https://www.ros.org/reps/rep-0144.html).

### Guidelines for Package Contents

When releasing a new package into a ROS distribution, the reviewers will check that the package has the following characteristics:

* The source repository must be publicly accessible.
* The license should be one of the open-source ones listed in [https://opensource.org/licenses](https://opensource.org/licenses) (preferably one of the "Popular licenses").
* The license must be reflected in the `package.xml` file of all sub-packages in the repository.
* A LICENSE file exists in the source repository.  This is because the short identifiers in the `package.xml` file aren't specific enough to unambiguously identify the license.
* The source repository should contain one or more ROS packages (meaning they have a `package.xml` in the source repository). Packages that are not ROS packages can be accepted, but they are rare and require special handling in the release repository.

For review simplicity, these rules apply to all packages, even ones that have previously been released into ROS 1 or ROS 2 distributions.

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

### Releasing third party system packages into a ROS distribution

In general you should not override or replace system dependencies from the system distribution with a package in the ROS distribution.
This is part of the software engineering process of maintaining the distribution that all developers can rely on specific versions of software to be available and remain consistent within the distribution.
If you truly need newer versions of underlying libraries then you can consider targeting a newer ROS distribution that targets a newer platform which hopefully will have a higher version of your necessary dependency.
If the necessary version of your dependency isn't available even on the latest platforms, please reach out and encourage the upstream operating systems to move forward to at least your minimum version for the next release of the upstream distributions.
By doing this you will make sure that it's available for everyone in the future.

Obviously this is a slow process and doesn’t fix things immediately.
There are workarounds such as embedding copies of the libraries into your package or making another package with the newer library version.
This usually can be made to work well in your local development environment.
However if you want to release this style of workaround into a ROS distribution you must make sure not to break other users who are expecting the system version either in downstream packages or elsewhere on the system.

To release a ROS package which will overlay a system dependency it must:

* Install side by side with the system one, with a different name.
* Not cause compile errors for any packages including downstream ones.
* Not cause linking errors or crashes at runtime for yours or any downstream packages, including ones that use the system version on any of our target platforms.

The release pipeline will only catch the first issue automatically.
Manual review is required for the latter two.
But in general if you want to do this without being disruptive you need to:
1. Adjust paths to avoid installation collisions.
2. Change all namespaces to avoid symbol collisions
3. Change header paths to not collide with the system ones if you export the include directories

Embedding a copy inside your package, potentially statically linking a version into your executables is another way to do it as well.
It’s going to require a non-trivial amount of engineering and modifications to make this possible and most people decide it’s not worth it.

In many situations a common approach for this is to not actually release it onto the public distro and distribute it separately through a side channel.
This will allow people to opt into the potentially disruptive change.
An example of this is Ubuntu’s PPAs or just instructions for end users to compile from source.

In the case that a package is released into a ROS distribution that is then later available in upstream system distributions when the ROS distribution rolls forward the ROS packages should be removed in favor of relying on the system version.
To provide a gentle transition, a placeholder package can be provided that only depends on the rosdep key.
This should be considered a deprecated package and dependent packages should switch to use the rosdep key.
This transitional package is likely something that should be scoped to be released into rolling only and not be in a subsequent released distribution.
It is up to the judgement of the ROS Distro's release manager to make an exception.

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

For convenience in reviewing, please comment in the PR with links to the web listings of packages such as on http://packages.ubuntu.com, http://packages.debian.org, and https://packages.fedoraproject.org or if a pip package pypi.python.org.

Please also briefly describe the package being added and what use case you want to use it for.
It's valuable to have a record of the packages as submitted and their intended purpose for clarity in the future so that if there's a conflict there's information to fall back on instead of speculation about the original use cases.

Guidelines for rosdep rules
---------------------------

 * Native packages are strongly preferred. (They are required for packaging and have upgrade and conflict tracking.)
 * Please use the smallest notation possible.
   For example if an ubuntu package is the same for all versions only write the generic ubuntu rule, don't call out the same package name for every version of ubuntu.
   Similarly don't call out indirect dependencies or default options for packages.
 * Python packages should go in the `python.yaml`.
 * The `osx-homebrew.yaml` file is deprecated; new macOS/Homebrew rules should go into either `base.yaml` or `python.yaml`.
 * Supported Platforms
   * Rules can be contributed for any platform.
     However to be released they must be at least cover the supported platforms in REP 3: http://www.ros.org/reps/rep-0003.html So:
    * Ubuntu and Debian are top priority.
    * Fedora and Gentoo have packaging jobs and should be filled in if they are available.
    * OSX is also nice to have.
    * NixOS is not required, but may be added if desired
    * If specific versions are called out, there should be coverage of all versions currently targeted by supported ROS distros.
     * If there's a new distro in prerelease adding a rule for it is fine.
       However please don't target 'sid' as it's a rolling target and when the keys change our database gets out of date.
    * Rules for EOL Distros will be pruned periodically.
      * If you are trying to use an EOL platform for historical purposes, you can access the old rules from tags of the rosdistro when that platform was supported, but there will not be any support or changes. [example](https://github.com/ros/rosdistro/issues/31569#issuecomment-1003974561)
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

Note that `pip` cannot be used to install system packages on Gentoo.
If the package is not present in the Gentoo package repository, please create an issue on the https://github.com/ros/ros-overlay repository so that it may be created at a later date, omit the key from the new rosdep rule, and link the created issue in the PR which is adding the rule. [Here's a simple example](https://github.com/ros/ros-overlay/issues/1019).

#### Arch Linux

Packages must be in the official Archlinux core, extra, or community repositories at the time they are contributed.

Packages in the AUR may not be added directly.
Work has been proposed to add a separate installer for AUR packages [ros-infrastructure/rosdep#560](https://github.com/ros-infrastructure/rosdep/issues/560).

#### Alpine Linux

* Alpine Linux requires the [`edge`](https://wiki.alpinelinux.org/wiki/Edge#Upgrading_to_Edge) release and [`testing`](https://wiki.alpinelinux.org/wiki/Aports_tree#testing) aports branch.

#### FreeBSD

* FreeBSD project pkg repository: main or quarterly
* A database of FreeBSD packages is available at https://freshports.org

#### NixOS/nixpkgs

* [NixOS unstable channel](https://github.com/NixOS/nixpkgs/tree/nixos-unstable), search available at https://search.nixos.org/packages
* [nix-ros-overlay](https://github.com/lopsided98/nix-ros-overlay)
* Following the [NixOS Python Guide](https://nixos.org/manual/nixpkgs/stable/#python), use `pythonPackages` for Python 2 and `python3Packages` for Python 3 keys.

#### openSUSE

* openSUSE Repositories: Pool and Updates
* You can search for packages on https://software.opensuse.org

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
  '*':
    pip:
      packages: [foobar]
```

In contrast to normal python entries, which are often different for python 2 and 3, pip entries for python 2 and 3 are almost always identical.
Hence no new entry would be needed. Though this would leave us with a mess of `python3-*`, `python-*-pip` and `python3-*-pip` entries.
To prevent this, the `python3-*-pip` entry should be mapped to the legacy `python-*-pip` entry by using yaml anchors and aliases.
(Preferably this was the other way around. So the `python3-*-pip` entry containing the contents and the anchor and the legacy `python-*-pip` entry being aliased to it.
Though the anchor should be defined before the anchor is used and `python3-` entries come after `python-` entries in alphabetical order.)

For example:

```yaml
python-foobar-pip: &migrate_eol_2025_04_30_python3_foobar_pip # Anchor
  '*':
    pip:
      packages: [foobar]
python3-foobar-pip: *migrate_eol_2025_04_30_python3_foobar_pip # Alias
```

The anchor/alias should be formatted as `migrate_eol_<YYYY>_<MM>_<DD>_<NEW_KEY_UNDERSCORED>`.

The EOL date of the entry should match the EOL date of the longest supported current platform.

Some existing rules do not have `python-` or `python3-` prefixes, but this is no longer recommended.
If the package ever becomes available in Debian or Ubuntu, the `python3-` prefix ensures that the `pip` key is next to it alphabetically.
The `-pip` key should be removed when the package becomes available on all platforms, and all existing users of the `-pip` key should migrate to the new key.

As a reminder `pip` rules should not be used on Gentoo.
See above for the Gentoo specific guidelines.

#### pip mixed with system packages

Some packages are only available as system packages in newer distributions.
In such case, you can specify the default as system package, and pip for older distributions for which the system packages are not available.

For example:

```yaml
python3-relatively-new-package
  ubuntu:
    '*': [python3-relatively-new-package]
    bionic:
      pip:
        packages: [relatively-new-package]
```

How to submit pull requests
---------------------------

When submitting pull requests it is expected that they pass the unit tests for formatting.
The unit tests enforce alphabetization of elements and a consistent formatting to keep merging as clean as possible.

### Unit Testing

It is recommended to use a virtual environment and pip to install the unit test dependencies.
The test dependencies are listed in [test/requirements.txt](./test/requirements.txt).

```bash
# create the virtual environment
python3 -m venv .venv

# "activate" the virtual environment
# this will let pip install dependencies into the virtual environment
# use activate.zsh if you use zsh, activate.fish if you use fish, etc.
source .venv/bin/activate

# install the dependencies
pip3 install -r test/requirements.txt

# run the tests!
pytest
```

It is highly recommended to run the unit tests before submitting a pull request.
(the CI system will run them anyways, but it will save you time)

