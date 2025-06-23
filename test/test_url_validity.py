#!/usr/bin/env python

# Copyright (c) 2017, Open Source Robotics Foundation
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

from __future__ import print_function
from . import hook_permissions

from io import StringIO
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import rosdistro
from scripts import eol_distro_names
import unidiff
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor

from .fold_block import Fold

# for commented debugging code below
# import pprint

UPSTREAM_NAME = 'unittest_upstream_comparison'
DIFF_BRANCH = 'master'
DIFF_REPO = 'https://github.com/ros/rosdistro.git'


TARGET_FILE_BLACKLIST = []


def get_all_distribution_filenames(url=None):
    if not url:
        url = rosdistro.get_index_url()
    distribution_filenames = []
    i = rosdistro.get_index(url)
    for d in i.distributions.values():
        for f in d['distribution']:
            dpath = os.path.abspath(urlparse(f).path)
            distribution_filenames.append(dpath)
    return distribution_filenames


def get_eol_distribution_filenames(url=None):
    if not url:
        url = rosdistro.get_index_url()
    distribution_filenames = []
    i = rosdistro.get_index(url)
    for d_name, d in i.distributions.items():
        if d_name in eol_distro_names:
            for f in d['distribution']:
                dpath = os.path.abspath(urlparse(f).path)
                distribution_filenames.append(dpath)
    return distribution_filenames


def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    # diffstr is already decoded
    io = StringIO(diffstr)
    udiff = unidiff.PatchSet(io)
    for file in udiff:
        target_lines = []
        # if file.path in TARGET_FILES:
        for hunk in file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[file.path] = target_lines
    return resultant_lines


def check_git_remote_exists(url, version, tags_valid=False, commits_valid=False):
    """ Check if the remote exists and has the branch version.
    If tags_valid is True query tags as well as branches """

    # Check for tags first as they take priority.
    # From Cloudbees Support:
    #  >the way git plugin handles this conflict, a tag/sha1 is always preferred to branch as this is the way most user use an existing job to trigger a release build.
    #  Catching the corner case to #20286

    tag_match = False
    cmd = ('git ls-remote %s refs/tags/*' % url).split()

    try:
        tag_list = subprocess.check_output(cmd).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        return (False, 'subprocess call %s failed: %s' % (cmd, ex))

    tags = [t for _, t in (l.split(None, 1) for l in tag_list.splitlines())]
    if 'refs/tags/%s' % version in tags:
        tag_match = True
    
    if tag_match:
        if tags_valid:
            return (True, '')
        else:
            error_str = 'Tags are not valid, but a tag %s was found. ' % version
            error_str += 'Re: https://github.com/ros/rosdistro/pull/20286'
            return (False, error_str)

    branch_match = False
    # check for branch name
    cmd = ('git ls-remote %s refs/heads/*' % url).split()

    commit_match = False
    # Only try to match a full length git commit id as this is an expensive operation
    if re.match('[0-9a-f]{40}', version):
        try:
            tmpdir = tempfile.mkdtemp()
            subprocess.check_call('git clone %s %s/git-repo' % (url, tmpdir), shell=True)
            # When a commit id is not found it results in a non-zero exit and the message
            # 'error: malformed object name...'.
            subprocess.check_call('git -C %s/git-repo branch -r --contains %s' % (tmpdir, version), shell=True)
            commit_match = True
        except:
            pass #return (False, 'No commit found matching %s' % version)
        finally:
            shutil.rmtree(tmpdir)

    if commit_match:
        if commits_valid:
            return (True, '')
        else:
            error_str = 'Commits are not valid, but a commit %s was found. ' % version
            error_str += 'Re: https://github.com/ros/rosdistro/pull/20286'
            return (False, error_str)

    # Commits take priority only check for the branch after checking for tags and commits first
    try:
        branch_list = subprocess.check_output(cmd).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        return (False, 'subprocess call %s failed: %s' % (cmd, ex))
    if not version:
        # If the above passed assume the default exists
        return (True, '')

    if 'refs/heads/%s' % version in branch_list:
        return (True, '')
    return (False, 'No branch found matching %s' % version)
    

def check_source_repo_entry_for_errors(source, tags_valid=False, commits_valid=False):
    errors = []
    if source['type'] != 'git':
        print('Cannot verify remote of type[%s] from line [%s] skipping.'
              % (source['type'], source['__line__']))
        return None

    version = source['version'] if source['version'] else None
    (remote_exists, error_reason) = check_git_remote_exists(source['url'], version, tags_valid, commits_valid)
    if not remote_exists:
        errors.append(
            'Could not validate repository with url %s and version %s from'
            ' entry at line %s. Error reason: %s'
            % (source['url'], version, source['__line__'], error_reason))
    test_pr = source['test_pull_requests'] if 'test_pull_requests' in source else None
    if test_pr:
        parsedurl = urlparse(source['url'])
        if 'github.com' in parsedurl.netloc:
            user = os.path.dirname(parsedurl.path).lstrip('/')
            repo, _ = os.path.splitext(os.path.basename(parsedurl.path))
            hook_errors = []
            rosghprb_token = os.getenv('ROSGHPRB_TOKEN', None)
            if not rosghprb_token:
                print('No ROSGHPRB_TOKEN set, continuing without checking hooks')
            else:
                hooks_valid = hook_permissions.check_hooks_on_repo(user, repo, hook_errors, hook_user='ros-pull-request-builder', callback_url='http://build.ros.org/ghprbhook/', token=rosghprb_token)
                if not hooks_valid:
                    errors += hook_errors
        else:
            errors.append('Pull Request builds only supported on GitHub right now. Cannot do pull request against %s' % parsedurl.netloc)
    if errors:
        return(" ".join(errors))
    return None


def check_repo_for_errors(repo):
    errors = []
    if 'source' in repo:
        source = repo['source']
        test_prs = source['test_pull_requests'] if 'test_pull_requests' in source else None
        test_commits = source['test_commits'] if 'test_commits' in source else None
        # Allow tags in source entries if test_commits and test_pull_requests are both explicitly false.
        tags_and_commits_valid = True if test_prs is False and test_commits is False else False
        source_errors = check_source_repo_entry_for_errors(repo['source'], tags_and_commits_valid, tags_and_commits_valid)
        if source_errors:
            errors.append('Could not validate source entry for repo %s with error [[[%s]]]' %
                          (repo['repo'], source_errors))
    if 'doc' in repo:
        source_errors = check_source_repo_entry_for_errors(repo['doc'], tags_valid=True, commits_valid=True)
        if source_errors:
            errors.append('Could not validate doc entry for repo %s with error [[[%s]]]' %
                          (repo['repo'], source_errors))
    return errors


def detect_post_eol_release(n, repo, lines):
    errors = []
    if 'release' in repo:
        release_element = repo['release']
        start_line = release_element['__line__']
        end_line = start_line
        if 'tags' not in release_element:
            print('Missing tags element in release section skipping')
            return []
        # There are 3 lines beyond the tags line. The tag contents as well as
        # the url and version number
        end_line = release_element['tags']['__line__'] + 3
        matching_lines = [l for l in lines if l >= start_line and l <= end_line]
        if matching_lines:
            errors.append('There is a change to a release section of an EOLed '
                          'distribution. Lines: %s' % matching_lines)
    if 'doc' in repo:
        doc_element = repo['doc']
        start_line = doc_element['__line__']
        end_line = start_line + 3
        # There are 3 lines beyond the tags line. The tag contents as well as
        # the url and version number
        matching_lines = [l for l in lines if l >= start_line and l <= end_line]
        if matching_lines:
            errors.append('There is a change to a doc section of an EOLed '
                          'distribution. Lines: %s' % matching_lines)

    return errors


def load_yaml_with_lines(filename):
    d = open(filename).read()
    loader = yaml.Loader(d)

    def compose_node(parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = loader.line
        node = Composer.compose_node(loader, parent, index)
        node.__line__ = line + 1
        return node

    construct_mapping = loader.construct_mapping

    def custom_construct_mapping(node, deep=False):
        mapping = construct_mapping(node, deep=deep)
        mapping['__line__'] = node.__line__
        return mapping
    loader.compose_node = compose_node
    loader.construct_mapping = custom_construct_mapping
    data = loader.get_single_data()
    return data


def isolate_yaml_snippets_from_line_numbers(yaml_dict, line_numbers):
    changed_repos = {}

    for dl in line_numbers:
        match = None
        for name, values in yaml_dict.items():
            if name == '__line__':
                continue
            if not isinstance(values, dict):
                print("not a dict %s %s" % (name, values))
                continue
            # print("comparing to repo %s values %s" % (name, values))
            if values['__line__'] <= dl:
                if match and match['__line__'] > values['__line__']:
                    continue
                match = values
                match['repo'] = name
        if match:
            changed_repos[match['repo']] = match
    return changed_repos


def main():
    detected_errors = []

    # See if UPSTREAM_NAME remote is available and use it as it's expected to be setup by CI
    # Otherwise fall back to origin/master
    try:
        cmd = ('git config --get remote.%s.url' % UPSTREAM_NAME).split()
        try:
            remote_url = subprocess.check_output(cmd).decode('utf-8').strip()
            # Remote exists
            # Check url
            if remote_url != DIFF_REPO:
                detected_errors.append('%s remote url [%s] is different than %s' % (UPSTREAM_NAME, remote_url, DIFF_REPO))
                return detected_errors

            target_branch = '%s/%s' % (UPSTREAM_NAME, DIFF_BRANCH)
        except subprocess.CalledProcessError:
            # No remote so fall back to origin/master
            print('WARNING: No remote %s detected, falling back to origin master. Make sure it is up to date.' % UPSTREAM_NAME)
            target_branch = 'origin/master'

        cmd = ('git diff --unified=0 %s' % target_branch).split()
        diff = subprocess.check_output(cmd).decode('utf-8')
    except subprocess.CalledProcessError as ex:
        detected_errors.append('%s' % ex)
        return detected_errors
    # print("output", diff)

    diffed_lines = detect_lines(diff)
    # print("Diff lines %s" % diffed_lines)


    for path, lines in diffed_lines.items():
        directory = os.path.join(os.path.dirname(__file__), '..')
        url = 'file://%s/index.yaml' % directory
        path = os.path.abspath(path)
        if path not in get_all_distribution_filenames(url):
            # print("not verifying diff of file %s" % path)
            continue
        with Fold():
            print("verifying diff of file '%s'" % path)
            is_eol_distro = path in get_eol_distribution_filenames(url)
            data = load_yaml_with_lines(path)

            repos = data['repositories']
            if not repos:
                continue

            changed_repos = isolate_yaml_snippets_from_line_numbers(repos, lines)

            # print("In file: %s Changed repos are:" % path)
            # pprint.pprint(changed_repos)

            for n, r in changed_repos.items():
                errors = check_repo_for_errors(r)
                detected_errors.extend(["In file '''%s''': " % path + e
                                        for e in errors])
                if is_eol_distro:
                    errors = detect_post_eol_release(n, r, lines)
                    detected_errors.extend(["In file '''%s''': " % path + e
                                            for e in errors])

    for e in detected_errors:

        print("ERROR: %s" % e, file=sys.stderr)
    return detected_errors


class TestUrlValidity(unittest.TestCase):

    def test_function(self):
        detected_errors = main()
        self.assertFalse(detected_errors)

if __name__ == "__main__":
    detected_errors = main()
    if not detected_errors:
        sys.exit(0)
    sys.exit(1)
