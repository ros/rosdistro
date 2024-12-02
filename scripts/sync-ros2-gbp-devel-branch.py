# Copyright (c) 2020, Open Source Robotics Foundation
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

# This is a program to sync rosdistro source entries with the release repository devel_branch.
#
# When doing a release of a ROS package through bloom, it is possible
# to set the branch in the rosdistro 'source' entry different from the
# "devel_branch" that is used in the release repository.  This is
# not recommended, as doing further releases will now cause bloom
# to look at the "wrong" branch for tags.  The situation gets even
# worse since both the rosdistro 'source' entry and the devel_branch
# in the release repository can be changed by hand.
#
# Overview
# --------
# This program starts by downloading the distribution.yaml file for a
# given ROS distribution, e.g. https://github.com/ros/rosdistro/blob/master/dashing/distribution.yaml
# In its default configuration, it will also download https://github.com/ros2/ros2/blob/master/ros2.repos
# in order to determine the "core" ROS 2 packages.  After finding the core packages,
# it will then go to the release repository for each package, and check to ensure that
# the devel_branch is the same as the branch listed on the rosdistro source entry.
# If they are different, it will open a pull request against the release
# distribution to synchronize them.
# Note that this program can produce false positives in corner cases, which is why it
# opens pull requests and doesn't directly push to the repositories.  The pull requests it
# generates should be carefully reviewed before merging.
#
# Dependencies
# ------------
# Besides the basic Python 3 dependency, this program relies on two external packages:
#  * https://pypi.org/project/PyGithub/
#  * https://pypi.org/project/keyring/
#
# Credentials
# -----------
# In order to do the work that it does, this program needs Github credentials in order to open pull requests.
# In the Github developer settings, create a new Personal Access Token that has full access to the `repo`
# permission and all sub-permissions.  When the token is created and it gives you a password, locally run:
#
# keyring set github-open-prs may-open-prs
#
# When it asks for a password, give it the token
#
# Usage
# -----
# usage: sync-ros-gbp-devel-branch.py [-h] [--all-repos] [--dry-run]
#                                     distribution
#
# positional arguments:
#   distribution  Which ROS distribution to do the sync for
#
# optional arguments:
#   -h, --help    show this help message and exit
#   --all-repos   Check all repositories, not just core ROS 2 ones
#   --dry-run     Just print the differences, do not actually open PRs

import argparse
import git
import github
import keyring
import os
import sys
import tempfile
import time
import urllib.request
import yaml


def get_ros2_core_repositories(ros_distro, ros_distro_yaml):
    # Now get the ros2.repos corresponding to this release, which we will use
    # to constrain the list of packages that we consider to be "core".
    ros2_repos_url = 'https://raw.githubusercontent.com/ros2/ros2/{ros_distro}/ros2.repos'.format(ros_distro=ros_distro)

    with urllib.request.urlopen(ros2_repos_url) as response:
        ros2_repos_data = response.read()

    ros2_repos_yaml = yaml.safe_load(ros2_repos_data)

    # Now build up the constrained list of packages to look at.
    constrained_list = []
    for repo in ros_distro_yaml['repositories']:
        repo_dict = ros_distro_yaml['repositories'][repo]
        if not 'source' in repo_dict:
            print("Package '{repo}' has no source entry, skipping".format(repo=repo))
            continue
        source_url = repo_dict['source']['url']

        item_to_delete = None
        for ros2_repo in ros2_repos_yaml['repositories']:
            ros2_repos_package_url = ros2_repos_yaml['repositories'][ros2_repo]['url']
            if ros2_repos_package_url == source_url:
                # OK, we found what we were looking for.  We are going to break
                # out of here and remove this from the list either way, but we
                # will only add it to the constrained_list if it has both a
                # 'release' section and it is on github.
                item_to_delete = ros2_repo
                if not 'release' in repo_dict:
                    print("No release section for package '{repo}', skipping".format(repo=repo))
                    break

                release_url = repo_dict['release']['url']
                if not release_url.startswith('https://github.com'):
                    print("Release URL {release_url} for package '{repo}' is not on GitHub, do not know how to fetch tracks.yaml data".format(release_url=release_url, repo=repo))
                    break

                constrained_list.append(repo_dict)
                break

        if item_to_delete is not None:
            del ros2_repos_yaml['repositories'][item_to_delete]

    return constrained_list


def get_all_ros2_repositories(ros_distro_yaml):
    constrained_list = []
    for repo in ros_distro_yaml['repositories']:
        repo_dict = ros_distro_yaml['repositories'][repo]
        if not 'source' in repo_dict:
            print("Package '{repo}' has no source entry, skipping".format(repo=repo))
            continue

        if not 'release' in repo_dict:
            print("No release section for package '{repo}', skipping".format(repo=repo))
            continue

        release_url = repo_dict['release']['url']
        if not release_url.startswith('https://github.com'):
            print("Release URL {release_url} for package '{repo}' is not on GitHub, do not know how to fetch tracks.yaml data".format(release_url=release_url, repo=repo))
            continue

        constrained_list.append(repo_dict)

    return constrained_list


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--all-repos', help='Check all repositories, not just core ROS 2 ones', action='store_true', default=False)
    parser.add_argument('--dry-run', help='Just print the differences, do not actually open PRs', action='store_true', default=False)
    parser.add_argument('distribution', nargs=1, help='Which ROS distribution to do the sync for', action='store')
    args = parser.parse_args()

    key = keyring.get_password('github-open-prs', 'may-open-prs')
    if key is None:
        raise RuntimeError('Failed to get GitHub API key')

    gh = github.Github(key)

    ros_distro = args.distribution[0]

    # First get the rosdistro distribution.yaml, which we will use as the source
    # of the devel_branch we should use.
    rosdistro_url = 'https://raw.githubusercontent.com/ros/rosdistro/master/{ros_distro}/distribution.yaml'.format(ros_distro=ros_distro)

    with urllib.request.urlopen(rosdistro_url) as response:
        ros_distro_data = response.read()

    ros_distro_yaml = yaml.safe_load(ros_distro_data)

    if args.all_repos:
        constrained_list = get_all_ros2_repositories(ros_distro_yaml)
    else:
        constrained_list = get_ros2_core_repositories(ros_distro, ros_distro_yaml)

    # Now that we have the list of repositories constrained, iterate over each
    # one, comparing what is in the tracks.yaml in the release repository to
    # what is in the source entry in the <distro>/distribution.yaml
    for repo in constrained_list:
        release_url = repo['release']['url']

        release_end = release_url[19:-4]
        tracks_url = 'https://raw.githubusercontent.com/' + release_end + '/master/tracks.yaml'

        with urllib.request.urlopen(tracks_url) as response:
            tracks_data = response.read()

        tracks_yaml = yaml.safe_load(tracks_data)
        tracks_yaml_distro = tracks_yaml['tracks'][ros_distro]

        if tracks_yaml_distro['devel_branch'] != repo['source']['version']:
            print("Package '{reponame}' rosdistro source branch ({source_branch}) does not match release branch ({release_branch})".format(reponame=tracks_yaml_distro['name'], source_branch=repo['source']['version'], release_branch=tracks_yaml_distro['devel_branch']))

            if args.dry_run:
                continue

            gh_body = """This PR from an automated script updates the devel_branch for {ros_distro} to match the source branch as specified in https://github.com/ros/rosdistro/{ros_distro}/distribution.yaml .
""".format(ros_distro=ros_distro)
            commit_message = """Change the devel_branch for {ros_distro}.

This makes it match the source entry in https://github.com/ros/rosdistro/{ros_distro}/distribution.yaml
""".format(ros_distro=ros_distro)

            branch_name = '{ros_distro}/sync-devel-branch'.format(ros_distro=ros_distro)

            with tempfile.TemporaryDirectory() as tmpdirname:
                gitrepo = git.Repo.clone_from(release_url, tmpdirname)
                gitrepo.git.checkout('master')
                branch = gitrepo.create_head(branch_name)
                branch.checkout()
                with open(os.path.join(tmpdirname, 'tracks.yaml'), 'r') as infp:
                    local_tracks_data = infp.read()
                local_tracks_yaml = yaml.safe_load(local_tracks_data)
                local_tracks_yaml['tracks'][ros_distro]['devel_branch'] = repo['source']['version']
                with open(os.path.join(tmpdirname, 'tracks.yaml'), 'w') as outfp:
                    yaml.dump(local_tracks_yaml, outfp)
                gitrepo.git.add(A=True)
                gitrepo.index.commit(commit_message.format(ros_distro=ros_distro))
                try:
                    gitrepo.git.push('--set-upstream', gitrepo.remote(), gitrepo.head.ref)
                except git.exc.GitCommandError:
                    print('Could not push to release repo for {ros_distro}: {reponame}, skipping...'.format(ros_distro=ros_distro, reponame=tracks_yaml_distro['name']))
                    continue

            gh_title = 'Update {ros_distro} devel_branch to match rosdistro source entry'.format(ros_distro=ros_distro)
            gh_repo = gh.get_repo(release_end)

            tries = 10
            succeeded = False
            while not succeeded and tries > 0:
                try:
                    pull = gh_repo.create_pull(title=gh_title, head=branch_name, base='master', body=gh_body)
                    succeeded = True
                except github.GithubException as e:
                    print('Failed to create pull request, waiting:', e)
                    time.sleep(30)
                    tries -= 1

            if tries == 0:
                print('Failed to create pull request and exceeded max tries, giving up')
                return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
