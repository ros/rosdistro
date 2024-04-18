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

from io import StringIO
import subprocess
import sys

import unidiff

def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    # diffstr is already decoded
    io = StringIO(diffstr)
    udiff = unidiff.PatchSet(io)
    for patched_file in udiff:
        target_lines = []
        # if file.path in TARGET_FILES:
        for hunk in patched_file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[patched_file.path] = target_lines
    return resultant_lines


def get_changed_line_numbers(path=''):
    UPSTREAM_NAME = 'unittest_upstream_comparison'
    DIFF_BRANCH = 'master'
    DIFF_REPO = 'https://github.com/ros/rosdistro.git'

    # See if UPSTREAM_NAME remote is available and use it as it's expected to be setup by CI
    # Otherwise fall back to origin/master
    cmd = ['git', 'config', '--get', 'remote.%s.url' % UPSTREAM_NAME]
    try:
        remote_url = subprocess.check_output(cmd).decode('utf-8').strip()
        # Remote exists
        # Check url
        assert remote_url == DIFF_REPO, \
            '%s remote url [%s] is different than %s' % (UPSTREAM_NAME, remote_url, DIFF_REPO)
        base_ref = '%s/%s' % (UPSTREAM_NAME, DIFF_BRANCH)
    except subprocess.CalledProcessError:
        # No remote so fall back to origin/master
        print('WARNING: No remote %s detected, falling back to origin master. Make sure it is up to date.' % UPSTREAM_NAME, file=sys.stderr)
        base_ref = 'origin/master'

    cmd = ['git', 'diff', '--unified=0', base_ref]
    if path:
        cmd.append('--')
        cmd.append(path)
    print("Detecting changed rules with '%s'" % (cmd,))
    diff = subprocess.check_output(cmd).decode('utf-8')
    return detect_lines(diff)
