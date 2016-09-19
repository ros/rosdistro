## aubo_robot (indigo) - 0.1.0-2

The packages in the `aubo_robot` repository were released into the `indigo` distro by running `/usr/bin/bloom-release --rosdistro indigo --track indigo aubo_robot --edit` on `Mon, 19 Sep 2016 07:28:44 -0000`

These packages were released:
- `aubo_control`
- `aubo_description`
- `aubo_driver`
- `aubo_gazebo`
- `aubo_i5_moveit_config`
- `aubo_kinematics`
- `aubo_msgs`
- `aubo_robot`
- `aubo_trajectory`

Version of package(s) in repository `aubo_robot`:

- upstream repository: https://github.com/auboliuxin/aubo_robot.git
- release repository: unknown
- rosdistro version: `null`
- old version: `0.1.0-1`
- new version: `0.1.0-2`

Versions of tools used:

- bloom version: `0.5.22`
- catkin_pkg version: `0.2.10`
- rosdep version: `0.11.5`
- rosdistro version: `0.4.7`
- vcstools version: `0.1.38`


## aubo_robot (indigo) - 0.1.0-1

The packages in the `aubo_robot` repository were released into the `indigo` distro by running `/usr/bin/bloom-release --rosdistro indigo --track indigo aubo_robot --edit` on `Mon, 19 Sep 2016 07:18:24 -0000`

These packages were released:
- `aubo_control`
- `aubo_description`
- `aubo_driver`
- `aubo_gazebo`
- `aubo_i5_moveit_config`
- `aubo_kinematics`
- `aubo_msgs`
- `aubo_robot`
- `aubo_trajectory`

Version of package(s) in repository `aubo_robot`:

- upstream repository: https://github.com/auboliuxin/aubo_robot.git
- release repository: unknown
- rosdistro version: `null`
- old version: `0.1.0-0`
- new version: `0.1.0-1`

Versions of tools used:

- bloom version: `0.5.22`
- catkin_pkg version: `0.2.10`
- rosdep version: `0.11.5`
- rosdistro version: `0.4.7`
- vcstools version: `0.1.38`


## aubo-robot (indigo) - 0.1.0-0

The packages in the `aubo-robot` repository were released into the `indigo` distro by running `/usr/bin/bloom-release --rosdistro indigo --track indigo aubo-robot --edit` on `Mon, 19 Sep 2016 05:51:17 -0000`

These packages were released:
- `aubo_control`
- `aubo_description`
- `aubo_driver`
- `aubo_gazebo`
- `aubo_i5_moveit_config`
- `aubo_kinematics`
- `aubo_msgs`
- `aubo_robot`
- `aubo_trajectory`

Version of package(s) in repository `aubo-robot`:

- upstream repository: https://github.com/auboliuxin/aubo_robot.git
- release repository: unknown
- rosdistro version: `null`
- old version: `null`
- new version: `0.1.0-0`

Versions of tools used:

- bloom version: `0.5.22`
- catkin_pkg version: `0.2.10`
- rosdep version: `0.11.5`
- rosdistro version: `0.4.7`
- vcstools version: `0.1.38`


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

