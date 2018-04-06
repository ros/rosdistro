This repo maintains the lists of repositories defining ROS 2 distributions.

It is an implementation of [REP 143](http://ros.org/reps/rep-0143.html)

The rosdep database in https://github.com/ros/rosdistro/tree/master/rosdep is used for ROS 2.

Guide to Contributing
---------------------

Please see [CONTRIBUTING.md](CONTRIBUTING.md)

A Quick Overview of How to Use this Repository
----------------------------------------------

To add your project to our build farm, fork this repository, modify the .yaml files, and give us a pull request.
Mappings for dependencies are maintained in the `rosdep` subfolder of https://github.com/ros/rosdistro

To create jobs on our build farm to build Debian sourcedeb and binarydeb packages add your bloom (or git-buildpackage compatible) repository to the `ROSDISTRO/distribution.yaml` file.
Please keep the alphabetic order of the list.

Files and directories:

 - index.yaml: list of ROS distributions (Groovy and newer) with references to their release, source and doc files
 - ROSDISTRO: the distribution files of each ROS distribution and their corresponding build files
 - scripts: support scripts

