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

import re

from . import find_package


_PYTHON_PATTERN = re.compile(r'^python(\d)-(.*)')


def make_suggestion(config, key, os_name):
    """
    Attempt to find packages which may satisfy a key based on the name.

    This function uses heuristics to suggest OS packages which may satisfy a
    key. Many of the heuristics do not apply to all platforms.

    :param config: the parsed YAML configuration.
    :param key: the name of the unsatisfied key.
    :param os_name: the name of the OS associated with the package.
    """
    os_version = config['supported_versions'][os_name][-1]
    os_arch = config['supported_arches'][os_name][0]
    # 1) Check for verbatim key
    suggestion = find_package(config, key, os_name, os_version, os_arch)
    if suggestion:
        print("Suggesting '%s' package for %s" % (suggestion.binary_name, os_name))
        return suggestion
    else:
        print("No '%s' package for %s %s (%s). Looking for variants..." % (
            key, os_name, os_version, os_arch))
    # 2) Try -devel in place of -dev
    if key.endswith('-dev'):
        suggestion = make_suggestion(config, key[:-4] + '-devel', os_name)
        if suggestion:
            return suggestion
    # 3) Try with 'lib' prefix
    if key.startswith('lib'):
        suggestion = make_suggestion(config, key[3:], os_name)
        if suggestion:
            return suggestion
    # 4) Try cmake(foo) and pkgconfig(foo)
    if key.endswith('-devel'):
        suggestion = make_suggestion(config, 'cmake(' + key[:-6] + ')', os_name)
        if suggestion:
            return suggestion
        suggestion = make_suggestion(config, 'pkgconfig(' + key[:-6] + ')', os_name)
        if suggestion:
            return suggestion
    # 5) Try python?dist(foo)
    py_match = _PYTHON_PATTERN.match(key)
    if py_match:
        suggestion = make_suggestion(
            config, 'python%sdist(%s)' % (py_match.group(1), py_match.group(2)), os_name)
        if suggestion:
            return suggestion
        if '-' in py_match.group(2):
            suggestion = make_suggestion(
                config, 'python%sdist(%s)' % (py_match.group(1), py_match.group(2).replace('-', '_')), os_name)
            if suggestion:
                return suggestion
