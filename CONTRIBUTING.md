
This repository acts as an index for the ROS distributions.
If you would like to add a package to the index you can either index it for just documentation, for binary builds or continuous integration tests. 
This repository also holds the rosdep rules. 

Binary Releases
---------------

If you would like to add a package for binary release please see the [Bloom documentation](http://wiki.ros.org/bloom).
Bloom is a tool which will help you do the release as well as open a pull-request for you.
It will also assist adding documentation and source entries.
There are [several helpful tutorials](http://wiki.ros.org/bloom/Tutorials) which provide instructions on how to do things like [make a first release](http://wiki.ros.org/bloom/Tutorials/FirstTimeRelease). 


Documentation Indexing
----------------------

If you just want to submit for documentation indexing only [this tutorial](http://wiki.ros.org/rosdistro/Tutorials/Indexing%20Your%20ROS%20Repository%20for%20Documentation%20Generation) will get you going. 

Continuous Integration Indexing
-------------------------------

If you would like to index your package for continuous integration tests you can add a source entry in the same way as the documentation index. 

rosdep rules contributions
--------------------------

This repository also holds the rosdep keys.
There is a guide for submitting rosdep keys [here](http://docs.ros.org/independent/api/rosdep/html/contributing_rules.html).
Updates to rosdep rules require the review of two people.
This will usually means that it needs a +1, and then it can be merged by a different person.

For convenience in reviewing please link to the web listings of packages such as on http://packages.ubuntu.com, http://packages.debian.org, and https://admin.fedoraproject.org/pkgdb/packages/ or if a pip package pypi.python.org.

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
 * If a package is only available via pip use the `-pip` extension.
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
   

How to submit pull requests
---------------------------

When submitting pull requests it is expected that they pass the unit tests for formatting. 
The unit tests enforce alphabetization of elements and a consistant formatting to keep merging as clean as possible. 

To run the tests run ``nosetests`` in the root of the repository.
They require the rosdistro library, available on Ubuntu with the ROS repositories as python-rosdistro or via pip as rosdistro.

There is a tool ``rosdistro_reformat`` which will fix most formatting errors such as alphabetization and correct formatting.
