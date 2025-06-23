# Copyright (c) 2021, Open Source Robotics Foundation
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

from io import StringIO
import os
import pprint
import subprocess
import sys
import unidiff
import unittest
import yaml

from . import get_package_link
from .config import load_config
from .suggest import make_suggestion
from .verify import verify_rules
from .yaml import AnnotatedSafeLoader
from .yaml import isolate_yaml_snippets_from_line_numbers


def detect_lines(diffstr):
    """Take a diff string and return a dict of files with line numbers changed."""
    resultant_lines = {}
    io = StringIO(diffstr)
    udiff = unidiff.PatchSet(io)
    for file in udiff:
        target_lines = []
        for hunk in file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[file.path] = target_lines
    return resultant_lines


def get_changed_line_numbers():
    UPSTREAM_NAME = 'unittest_upstream_comparison'
    DIFF_BRANCH = 'master'
    DIFF_REPO = 'https://github.com/ros/rosdistro.git'

    # See if UPSTREAM_NAME remote is available and use it as it's expected to be setup by CI
    # Otherwise fall back to origin/master
    cmd = 'git config --get remote.%s.url' % UPSTREAM_NAME
    try:
        remote_url = subprocess.check_output(cmd.split()).decode('utf-8').strip()
        # Remote exists
        # Check url
        assert remote_url == DIFF_REPO, \
            '%s remote url [%s] is different than %s' % (UPSTREAM_NAME, remote_url, DIFF_REPO)
        base_ref = '%s/%s' % (UPSTREAM_NAME, DIFF_BRANCH)
    except subprocess.CalledProcessError:
        # No remote so fall back to origin/master
        print('WARNING: No remote %s detected, falling back to origin master. Make sure it is up to date.' % UPSTREAM_NAME, file=sys.stderr)
        base_ref = 'origin/master'

    cmd = 'git diff --unified=0 %s -- rosdep' % (base_ref,)
    print("Detecting changed rules with '%s'" % (cmd,))
    diff = subprocess.check_output(cmd.split()).decode('utf-8')
    return detect_lines(diff)


class TestRosdepRepositoryCheck(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls._changed_lines = get_changed_line_numbers()
        cls._config = load_config()
        cls._full_data = {}
        cls._isolated_data = {}
        cls._repo_root = os.path.join(os.path.dirname(__file__), '..', '..')

        # For clarity in the logs, show as 'skipped' rather than 'passed'
        if not cls._changed_lines:
            raise unittest.SkipTest('No rosdep changes were detected')

        for path in ('rosdep/base.yaml', 'rosdep/python.yaml'):
            if path not in cls._changed_lines:
                continue
            with open(os.path.join(cls._repo_root, path)) as f:
                cls._full_data[path] = yaml.load(f, Loader=AnnotatedSafeLoader)
            isolated_data = isolate_yaml_snippets_from_line_numbers(
                cls._full_data[path], cls._changed_lines[path])
            if not isolated_data:
                continue
            cls._isolated_data[path] = isolated_data
            pprint.pprint(isolated_data)

    def test_rosdep_repo_check(self):
        broken = False

        for path, data in self._isolated_data.items():
            print("Verifying the following rosdep rules in '%s':" % path)
            results = verify_rules(
                self._config, data, self._full_data[path], include_found=True)
            for os_name, os_ver, os_arch, key, package, provider in results:
                if not provider:
                    broken = True
                    print(
                        '\n::error file=%s,line=%d::'
                        "Package '%s' could not be found for %s %s on %s" % (
                            path, getattr(os_ver, '__line__', os_name.__line__),
                            package, os_name, os_ver, os_arch),
                        file=sys.stderr)
                else:
                    provider_url = get_package_link(
                        self._config, provider, os_name, os_ver, os_arch)
                    print(
                        "Package '%s' for %s %s on %s was found: %s" % (
                            package, os_name, os_ver, os_arch, provider_url),
                        file=sys.stderr)

        assert not broken, 'New rules contain packages not present in repositories'

    def test_suggest_by_name(self):
        for path, data in self._isolated_data.items():
            print("Looking for name-based suggestions in '%s':" % path)
            for key in data.keys():
                if key.endswith('-pip'):
                    # Ignore pip stuff to save time
                    continue
                if getattr(key, '__line__', None) not in self._changed_lines[path]:
                    continue
                rules = self._full_data[path][key]
                missing_os_names = set(
                    self._config['supported_versions'].keys()).difference(rules.keys())
                for missing_os in missing_os_names:
                    print('Looking for suggestions for %s on %s' % (key, missing_os))
                    suggestion = make_suggestion(self._config, key, missing_os)
                    if suggestion:
                        suggestion_url = get_package_link(
                            self._config, suggestion, missing_os,
                            self._config['supported_versions'][missing_os][-1],
                            self._config['supported_arches'][missing_os][0])
                        print(
                            '\n::warning file=%s,line=%d::'
                            "Key '%s' might be satisfied by %s package named '%s': %s" % (
                                path, key.__line__, key, missing_os, suggestion.binary_name,
                                suggestion_url),
                            file=sys.stderr)
