# Copyright (c) 2026, Open Source Robotics Foundation
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

import json
import posixpath

from . import open_compressed_url
from . import PackageEntry
from . import RepositoryCacheCollection


def replace_tokens(string, os_code_name, os_arch):
    """Replace tokens in the repository base URL."""
    for key, value in {
        '$arch': os_arch,
        '$releasever': os_code_name,
    }.items():
        string = string.replace(key, value)
    return string


def enumerate_conda_packages(url_template, os_name, os_code_name, os_arch):
    """
    Enumerate packages in a conda channel repository.

    :param url_template: the conda repodata file URL or URL template.
    :param os_name: the name of the OS associated with the repository.
    :param os_code_name: the OS version associated with the repository.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """
    repodata_url = replace_tokens(url_template, os_code_name, os_arch)
    channel_url = posixpath.dirname(repodata_url)
    print('Reading conda package metadata from ' + repodata_url)
    with open_compressed_url(repodata_url) as f:
        data = json.load(f)

    for pkgs_key in ('packages', 'packages.conda'):
        for fn, pkg_info in data.get(pkgs_key, {}).items():
            name = pkg_info.get('name')
            version = pkg_info.get('version')
            if name and version:
                pkg_url = posixpath.join(channel_url, fn)
                yield PackageEntry(name, version, pkg_url)


def conda_channel_url(url_template):
    """
    Create an enumerable cache for a conda channel repository.

    :param url_template: the URL or URL template of the conda channel.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_conda_packages(url_template, os_name, os_code_name, os_arch))
