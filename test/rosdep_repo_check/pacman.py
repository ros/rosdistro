# Copyright (c) 2022, Open Source Robotics Foundation
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

import os
import tarfile

from . import open_compressed_url
from . import PackageEntry
from . import RepositoryCacheCollection


def replace_tokens(string, repo_name, os_arch):
    """Replace pacman-specific tokens in the repository base URL."""
    for key, value in {
        '$arch': os_arch,
        '$repo': repo_name,
    }.items():
        string = string.replace(key, value)
    return string


def enumerate_descs(url):
    """
    Enumerate desc files from a pacman db.

    :param url: the URL of the pacman db.

    :returns: an enumeration of desc file contents.
    """
    with open_compressed_url(url) as f:
        with tarfile.open(mode='r|', fileobj=f) as tf:
            for ti in tf:
                if ti.name.endswith('/desc'):
                    yield tf.extractfile(ti)


def enumerate_blocks(url):
    """
    Enumerate blocks of mapped data from a pacman db.

    :param url: the URL of the pacman db.

    :returns: an enumeration of mappings.
    """
    for desc in enumerate_descs(url):
        block = {}
        while True:
            k = desc.readline()
            if not k:
                break
            k = k.strip().decode()
            if not k:
                continue

            v = []
            while True:
                line = desc.readline().strip().decode()
                if not line:
                    break
                v.append(line)

            block[k] = v

        if block: 
            yield block


def enumerate_pacman_packages(base_url, repo_name, os_arch):
    """
    Enumerate pacman packages in a repository.

    :param base_url: the pacman repository base URL.
    :param repo_name: the name of the repository to enumerate.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """
    base_url = replace_tokens(base_url, repo_name, os_arch)
    db_url = os.path.join(base_url, repo_name + '.db.tar.gz')
    print('Reading pacman package metadata from ' + db_url)
    for block in enumerate_blocks(db_url):
        pkg_url = os.path.join(base_url, block['%FILENAME%'][0])
        pkg_name = block['%NAME%'][0]
        pkg_ver = block['%VERSION%'][0]
        yield PackageEntry(pkg_name, pkg_ver, pkg_url)
        for pkg_prov in block.get('%PROVIDES%', ()):
            yield PackageEntry(pkg_prov, pkg_ver, pkg_url, pkg_name, pkg_name)


def pacman_base_url(base_url, repo_name):
    """
    Create an enumerable cache for a pacman repository.

    :param base_url: the URL of the pacman repository.
    :param repo_name: the name of the repository to enumerate.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_pacman_packages(base_url, repo_name, os_arch))
