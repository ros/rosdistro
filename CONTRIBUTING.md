
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


How to submit pull requests
---------------------------

When submitting pull requests it is expected that they pass the unit tests for formatting. 
The unit tests enforce alphabetization of elements and a consistant formatting to keep merging as clean as possible. 

To run the tests run ``nosetests`` in the root of the repository.
They require the rosdistro library, available on Ubuntu with the ROS repositories as python-rosdistro or via pip as rosdistro.

There is a tool ``rosdistro_reformat`` which will fix most formatting errors such as alphabetization and correct formatting.
