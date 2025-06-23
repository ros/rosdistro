<!-- Thank you for contributing a change to the rosdistro. There are two primary types of submissions.
Please select the appropriate template from below: ROSDEP_RULE_TEMPLATE or DOC_INDEX_TEMPLATE

If you're making a new release with bloom please use bloom to create the pull request automatically (except for the naming review request which must be made manually).
If you've already run the release bloom has a `--pull-request-only` option you can use.-->

<!-- ROSDEP_RULE_TEMPLATE: Submitter Please review the contributing guidelines: https://github.com/ros/rosdistro/blob/master/CONTRIBUTING.md -->

Please add the following dependency to the rosdep database.

## Package name:

TODO

## Package Upstream Source:

TODO link to source repository

## Purpose of using this:

TODO Replace. This dependency is being used for this reason. This is why I think it's valuable to be added to the rosdep database.

Distro packaging links:

## Links to Distribution Packages

<!-- Replace the REQUIRED areas with the URL to the package.  For IF AVAILABLE areas, either put in the URL to the package or state 'not available'.
More info at https://github.com/ros/rosdistro/blob/master/CONTRIBUTING.md#guidelines-for-rosdep-rules -->

- Debian: https://packages.debian.org/
  - REQUIRED
- Ubuntu: https://packages.ubuntu.com/
  - REQUIRED
- Fedora: https://packages.fedoraproject.org/
  - IF AVAILABLE
- Arch: https://www.archlinux.org/packages/
  - IF AVAILABLE
- Gentoo: https://packages.gentoo.org/
  - IF AVAILABLE
- macOS: https://formulae.brew.sh/
  - IF AVAILABLE
- Alpine: https://pkgs.alpinelinux.org/packages
  - IF AVAILABLE
- NixOS/nixpkgs: https://search.nixos.org/packages
  - OPTIONAL
- openSUSE: https://software.opensuse.org/package/
  - IF AVAILABLE
- rhel: https://rhel.pkgs.org/
  - IF AVAILABLE

<!-- DOC_INDEX_TEMPLATE: add package to rosdistro for documentation indexing -->

<!--- Templated for adding a package to be indexed in a rosdistro: http://wiki.ros.org/rosdistro/Tutorials/Indexing%20Your%20ROS%20Repository%20for%20Documentation%20Generation -->

# Please Add This Package to be indexed in the rosdistro.

ROSDISTRO NAME

# The source is here:

http://sourcecode_url

# Checks
 - [ ] All packages have a declared license in the package.xml
 - [ ] This repository has a LICENSE file
 - [ ] This package is expected to build on the submitted rosdistro
