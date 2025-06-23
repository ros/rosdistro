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

import os

from . import open_gz_url
from . import PackageEntry
from . import RepositoryCacheCollection


def enumerate_blocks(url):
    """
    Enumerate blocks of mapped data from a URL to a text file.

    :param url: the URL of the text file.

    :returns: an enumeration of mappings.
    """
    block = {}
    key = None
    with open_gz_url(url) as f:
        while True:
            line = f.readline().decode('utf-8')
            if not len(line):
                break
            elif line[0] in ['\r', '\n']:
                yield block
                block = {}
                key = None
                continue
            elif line[0] in [' ', '\t']:
                # This is a list element
                if not key:
                    raise ValueError('list element at block beginning')
                if not isinstance(block[key], list):
                    block[key] = [block[key]] if block[key] else []
                block[key].append(line.strip())
                continue
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if not key:
                raise ValueError('empty key')
            block[key] = val
    if block:
        yield block


def enumerate_deb_packages(base_url, comp, os_code_name, os_arch):
    """
    Enumerate debian packages in a repository.

    :param base_url: the debian repository base URL.
    :param comp: the component of the repository to enumerate.
    :param os_code_name: the OS version associated with the repository.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """
    pkgs_url = os.path.join(base_url, 'dists', os_code_name,
                            comp, 'binary-' + os_arch, 'Packages.gz')
    print('Reading debian package metadata from ' + pkgs_url)
    for block in enumerate_blocks(pkgs_url):
        pkg_url = os.path.join(base_url, block['Filename'])
        yield PackageEntry(block['Package'], block['Version'], pkg_url,
                           block.get('Source', block['Package']))


def deb_base_url(base_url, comp):
    """
    Create an enumerable cache for a debian repository.

    :param base_url: the URL of the debian repository.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_deb_packages(base_url, comp, os_code_name, os_arch))
