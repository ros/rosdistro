This repo maintains the lists of repositories defining ROS distributions.

To add your project to our build farm, fork this repository, modify the .yaml files under ``releases`` or ``rosdep``, and give us a pull request.

To create jobs on our build farm to build Debian sourcedeb and binarydeb packages add your git-buildpackage repository to the ``releases/ROSDISTRO.yaml`` file.
Please keep the alphabetic order of the list.
You can use the script ``scripts/add_release_repo.py`` to perform the insertion.

To create jobs on our build farm to perform continuous integration of your repository on every commit add your source repository to the ``releases/ROSDISTRO-devel.yaml`` file.
Please keep the alphabetic order of the list.
You can use the script ``scripts/add_devel_repo.py`` to perform the insertion.

Directories:

 - releases: list of released resources (e.g. GBP distro files) and targets configuration  
 - rosdep: rosdep YAML files and default configuration
 - scripts: support scripts
