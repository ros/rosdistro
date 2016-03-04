This repo maintains the lists of repositories defining ROS distributions.

It is the implementation of [REP 143](http://ros.org/reps/rep-0143.html)

It also the home of the rosdep rules.

Guide to Contributing
---------------------

Please see [CONTRIBUTING.md](CONTRIBUTING.md)

A Quick Overview of How to Use this Repository
----------------------------------------------

To add your project to our build farm, fork this repository, modify the .yaml files, and give us a pull request.
For Fuerte and older the ROS packages are maintained in the subfolder ``releases`` and ``doc``.
For Groovy and newer the ROS packages are maintained in the subfolder named after the ROS distribution.
Mappings for dependencies are maintained in the ``rosdep`` subfolder.

To create jobs on our build farm to build Debian sourcedeb and binarydeb packages add your bloom (or git-buildpackage compatible) repository to the ``ROSDISTRO/release.yaml`` file (or ``releases/ROSDISTRO.yaml`` for Fuerte and older).
Please keep the alphabetic order of the list.
You can use the script ``scripts/add_release_repo.py`` to perform the insertion.

To create jobs on our build farm to perform continuous integration of your repository on every commit add your source repository to the ``ROSDISTRO/source.yaml`` file (or ``releases/ROSDISTRO-devel.yaml`` for Fuerte and older).
Please keep the alphabetic order of the list.
You can use the script ``scripts/add_devel_repo.py`` to perform the insertion.

Files and directories:

 - index.yaml: list of ROS distributions (Groovy and newer) with references to their release, source and doc files
 - ROSDISTRO: the release, source and doc files of the ROS distribution and their corresponding build files
 - releases: list of released resources (e.g. GBP distro files) and targets configuration (Fuerte and older)
 - rosdep: rosdep YAML files and default configuration
 - scripts: support scripts

