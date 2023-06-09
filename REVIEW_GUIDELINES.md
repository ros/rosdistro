rosdistro Review Guidelines
===========================

Summary
-------
The goal of this document is to explain the different kinds of pull requests that are typically opened against this repository, and what a reviewer will do for each of the cases.

Purpose of this repository
--------------------------
This repository acts as the repository of packages that are "released" into a ROS distribution. To add a new package to a ROS distribution, one can either manually open a pull request to rosdistro, or use bloom-release to create the pull request (preferred).

Rosdistro also acts as a database of system packages that ROS packages depend on.
For instance, if a ROS package depends on a system package called `zziplib`, then there must be a corresponding entry in the rosdep database.
The rosdep database is the mapping of keys to specific Linux distribution package names, since the same package can have different names in different Linux distributions. rosdep ensures dependencies can be installed with a common name (key) across all Linux distributions.

There are currently two main files that contain rosdep entries:

* [python.yaml](rosdep/python.yaml): python dependencies of any ROS packages, including "pip" packages
* [base.yaml](rosdep/base.yaml): everything else

Note: ROS packages that depend on "pip" keys cannot be "released" into a ROS distribution.
They can only be depended on by from-source builds.
Because of this, system packages are highly preferred to pip packages.

ROS Distribution Freezes
------------------------
Approximately every two weeks, the ROS Boss of the corresponding ROS distribution will do a sync, which updates existing packages and releases new packages of the ROS distribution to the general public.
Prior to the sync, the ROS Boss will announce a "sync freeze" on [Discourse](https://discourse.ros.org/).
During the sync freeze, no new packages or package updates will be merged into that particular ROS distribution without the express consent of the ROS Boss.
Every ROS distribution is on a different sync schedule.

Types of Pull Requests
----------------------
There are a few different types of pull requests that are opened against this repository (these are in order of most likely to least likely to happen):

1.  A version update to an existing package in a ROS distribution.  An example of this kind of PR is [25822](https://github.com/ros/rosdistro/pull/25822).  In these types of pull requests, the package owner is updating a major, minor, patch, or debinc number in the package.  As long as the ROS distribution isn’t in a “sync freeze” and the bloom-version meets the [current minimum requirements](https://docs.ros.org/en/ros2_documentation/rolling/Guides/Releasing-a-ROS-2-package-with-bloom.html#required-tools) these PRs will be merged without further review.  If the ROS distribution is in a "sync freeze", the PR will be approved with a note saying something like “Holding for sync freeze” with a link to the relevant discourse post. Once the distribution is out of sync freeze, these PRs will then be merged.

1.  A new binary, source, or documentation package in a ROS distribution.  An example of this kind of PR is [25857](https://github.com/ros/rosdistro/pull/25857).  In this type of PR, any combination of (`release`, `doc`, and `source`) fields are permitted.  If an entry has a `release` field, the PR should generally have been opened via bloom; if it wasn't, the reviewer will ask why.  There are two sub-categories of this kind of PR:
    1.  If the package has been released into a prior ROS distribution, then the reviewer will ensure that the URLs to the doc, release, and source entries are the same as in the previous releases (this will be checked either by looking for the package in a previous distro's distribution.yaml file, or by looking at the release repository for a branch named release/{distro}).  If the URLs are different, then the reviewer will ask the submitter why the URLs are different and whether it can be combined into the original one.
    1.  For packages that are brand-new to the ROS ecosystem, some due diligence will be done on the source and release repositories:
        * There must be a LICENSE file. Either each package in the repository should have a LICENSE file, or the source repository should have a top-level LICENSE file. If the repository is under multiple licenses, then it is encouraged (but not required) to have one LICENSE.<name> file per license. The LICENSE file only needs to be in the sources; a new release after adding a LICENSE file is *not* required.
        * The license should be one of the open-source ones listed in [https://opensource.org/licenses](https://opensource.org/licenses) (preferably one of the "Popular licenses").
        * The license must be reflected in the package.xml file of all sub-packages in the repository.
        * The source repository must be publicly accessible.
        * The source repository should contain one or more ROS packages (meaning they have a `package.xml` in the source repository). Packages that are not ROS packages can be accepted, but they are rare and require special handling in the release repository.
        * The name of the repository and the packages within it must comply with the guidelines in [REP-144](https://www.ros.org/reps/rep-0144.html).
    1. The best practices for Rolling releases is to use a release repository in the https://github.com/ros2-gbp organization. That way this package can be automatically released from Rolling into the next stable ROS distribution.  There are instructions in https://github.com/ros2-gbp/ros2-gbp-github-org/blob/latest/CONTRIBUTING.md describing how to create one.

    Once the above criteria are satisfied, and the ROS distribution isn't in a "sync freeze", then the PR will be merged.

1.  A new rosdep key.  An example of this kind of PR is [25995](https://github.com/ros/rosdistro/pull/25995). These pull requests should conform to the standards documented at [CONTRIBUTING.md#rosdep-rules-contributions](CONTRIBUTING.md#rosdep-rules-contributions). Some rules in addition to contributing guidelines:
    * A pull request to update rosdep should never change the name of existing keys.
    * When adding a new key, Ubuntu and Debian are required, Fedora, Gentoo, and openSUSE are encouraged if the package also exists on those Linux distributions.
    * Native packages are strongly preferred.  If a native package exists for the key in question, then that should always be used over e.g. a pip key.
    * If a native package is available, the key name should match the name of the package in Ubuntu.
    * If a package was added to e.g. Ubuntu Focal but isn’t available in Bionic or Xenial, the key should look like:
    ```
    mykey:
      ubuntu:
        '*': [mykey]
        bionic: null
        xenial: null
    ```
    * New rosdep keys are typically only accepted for supported Ubuntu distros which have ROS releases; the ROS support timeline generally follows the Ubuntu LTS support timeline.
    * If there is no good alternative for a pip package to add to rosdep keys, use `python3-PACKAGENAME-pip` to name the key.
    * If a key conforms to all standards above, then it can be approved. Once the pull request has two approvals, it will be merged.

1.  A revert of an existing package.  This can happen if the package in question can’t be built on the farm for some reason, or the maintainer doesn’t want to maintain it, or for various other reasons.  An example of this kind of PR is [26427](https://github.com/ros/rosdistro/pull/26427).  If a package was previously merged into rosdistro, but has never been synced to main, these will be merged right away (no downstream users could have installed them).  If a package *has* been synced to main, it is still safe to remove it.  However, the submitter should be aware that the package will disappear from ROS completely; no old versions will be kept around for users to install.  The reviewer will ensure that the maintainer is aware of that limitation.  If the submitter is OK with that situation, then these will be merged.  It can be determined if a package has been synced to main by visiting either [ROS 1 Status](http://repositories.ros.org/status_page) or [ROS 2 Status](http://repo.ros2.org/status_page/), and clicking on the distribution in question.  For instance, to look up Melodic, click on [http://repositories.ros.org/status_page/ros_melodic_default.html](http://repositories.ros.org/status_page/ros_melodic_default.html).  The package can be searched for on the top bar.  The three boxes to the right of the package name determine its status in the "building", "testing", and "main" repositories.  If a package is red in "main", then it has never been synced to main.

1.  Changes to the rosdistro code. These pull requests change any of the scripts or tests that are housed in the rosdistro repositories.  They will be reviewed as any other code change in the ROS ecosystem.

1.  Miscellaneous. Any other pull requests adding or modifying documentation, or anything else will be reviewed as any other code change in the ROS ecosystem.

Reviewer utilities
------------------

### New package review checklist

You can copy-paste the below into your review comment when reviewing a new package addition into rosdistro.

- [ ] At least one of the following must be present
  - [ ] Top level license file:
  - [ ] Per package license files:
- [ ] License is [OSI-approved](https://opensource.org/licenses):
- [ ] License correctly listed in package.xmls
- [ ] Public source repo:
- [ ] Source repository contains ROS packages
- [ ] Each package meets [REP-144](https://www.ros.org/reps/rep-0144.html) naming conventions

<details><summary>Package name details</summary>

```console
$ find . -name "package.xml" -exec grep --color=auto -e "<name>" "{}" ";"
<OUTPUT HERE>
```
</details>

<details><summary>License details</summary>

```console
$ find . -name "package.xml" -exec grep --color=auto -e "<license>" "{}" "+"
<OUTPUT HERE>
```
</details>

### pip keys standard disclaimer

You can copy-paste the following as a comment when reviewing a new rosdistro key using `pip` (even if you are approving!)

Standard pip disclaimer: ROS packages that depend on `pip` keys cannot be released into a ROS distribution.
They can only be depended on by from-source builds.
Because of this, system packages are highly preferred to pip packages.
