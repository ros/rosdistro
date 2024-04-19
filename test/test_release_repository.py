# Copyright (c) 2024, Open Source Robotics Foundation
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Willow Garage, Inc. nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# This is a test to ensure that all release repositories in a given
# distribution (rolling, for now) are in the ros2-gbp organization.

import os
import sys
import unittest

import yaml

from .get_changed_lines import get_changed_line_numbers


DISTRIBUTIONS_TO_CHECK = {
    'humble': ['affordance_primitives', 'aruco_ros', 'bcr_bot', 'behaviortree_cpp_v3', 'boost_plugin_loader', 'clearpath_common', 'clearpath_config', 'clearpath_desktop', 'clearpath_msgs', 'clearpath_nav2_demos', 'clearpath_simulator', 'cob_common', 'create_robot', 'dataspeed_can', 'dbw_ros', 'depthai', 'depthai-ros', 'etsi_its_messages', 'fadecandy_ros', 'flir_camera_driver', 'grasping_msgs', 'hey5_description', 'hri', 'hri_msgs', 'human_description', 'interactive_marker_twist_server', 'launch_pal', 'libcreate', 'librealsense2', 'lms1xx', 'lsc_ros2_driver', 'lusb', 'marker_msgs', 'marvelmind_ros2_msgs', 'marvelmind_ros2_release', 'mocap4r2', 'mocap4r2_msgs', 'mod', 'nao_meshes', 'naoqi_bridge_msgs2', 'naoqi_driver', 'naoqi_libqi', 'naoqi_libqicore', 'navigation2', 'nerian_stereo_ros2', 'network_interface', 'novatel_oem7_driver', 'omni_base_navigation', 'omni_base_robot', 'pal_gazebo_plugins', 'pal_gazebo_worlds', 'pal_gripper', 'pal_hey5', 'pal_navigation_cfg_public', 'pal_robotiq_gripper', 'pal_urdf_utils', 'pepper_meshes', 'play_motion2', 'pmb2_navigation', 'pmb2_robot', 'pmb2_simulation', 'popf', 'qb_softhand_industry', 'realsense2_camera', 'robot_controllers', 'robot_upstart', 'robotraconteur', 'ros2_planning_system', 'rtabmap_ros', 'rviz_satellite', 'sick_safetyscanners2', 'sick_safetyscanners2_interfaces', 'sick_safetyscanners_base', 'simple_term_menu_vendor', 'slam_toolbox', 'smacc2', 'tiago_moveit_config', 'tiago_navigation', 'tiago_robot', 'tiago_simulation', 'turtlebot3', 'tuw_msgs', 'urdf_sim_tutorial', 'urdf_test', 'weight_scale_interfaces', 'wireless', 'wrapyfi_ros2_interfaces'],
    'iron': ['azure-iot-sdk-c', 'depthai', 'depthai-ros', 'etsi_its_messages', 'flir_camera_driver', 'grasping_msgs', 'interactive_marker_twist_server', 'libcreate', 'librealsense2', 'nao_meshes', 'naoqi_bridge_msgs2', 'naoqi_driver', 'naoqi_libqi', 'naoqi_libqicore', 'navigation2', 'nerian_stereo_ros2', 'nonpersistent_voxel_layer', 'pepper_meshes', 'realsense2_camera', 'robotraconteur', 'rtabmap_ros', 'rviz_satellite', 'sick_safetyscanners2', 'sick_safetyscanners2_interfaces', 'sick_safetyscanners_base', 'slam_toolbox', 'urdf_sim_tutorial'],
    'rolling': [],
}


def check_one_distribution(distro, exceptions, diffed_lines):
    distro_file = os.path.join(distro, 'distribution.yaml')
    if not distro_file in diffed_lines:
        return 0

    # If there were changes to one of the distribution.yaml, parse the entire
    # thing, and check every repository to make sure it is a ros2-gbp one.

    for path, lines in diffed_lines.items():
        if path == distro_file:
            full_path = os.path.abspath(path)
            break
    else:
        # This should never happen
        print('Expected to find a full path to the distribution file, found nothing')
        return 1

    with open(full_path, 'r') as infp:
        data = yaml.safe_load(infp)

    for repo, info in data['repositories'].items():
        if 'release' not in info:
            continue

        if repo in exceptions:
            continue

        release_repo_url = info['release']['url']

        if not release_repo_url.startswith('https://github.com/ros2-gbp'):
            print(f'Expected release repository for "{repo}" in ROS distribution "{distro}" to be in the https://github.com/ros2-gbp organization')
            return 2

    return 0


def main():
    diffed_lines = get_changed_line_numbers()
    if not diffed_lines:
        # No changes, just silently exit
        return 0

    for distro, exceptions in DISTRIBUTIONS_TO_CHECK.items():
        ret = check_one_distribution(distro, exceptions, diffed_lines)
        if ret != 0:
            return ret

    return 0


class TestReleaseRepositoryGBP(unittest.TestCase):

    def test_release_repository_gbp(self):
        self.assertTrue(main() == 0)

if __name__ == "__main__":
    sys.exit(main())
