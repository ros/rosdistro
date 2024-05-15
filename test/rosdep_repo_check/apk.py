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
import tarfile

from . import open_compressed_url
from . import PackageEntry
from . import RepositoryCacheCollection


def parse_apkindex(f):
    # An example of an APKINDEX entry. Entries are divided by a blank line.

    # V:2.1.1-r0
    # A:x86_64
    # S:6645
    # I:28672
    # T:RTP proxy (documentation)
    # U:https://www.rtpproxy.org/
    # L:BSD-2-CLause
    # o:rtpproxy
    # m:Natanael Copa <ncopa@alpinelinux.org>
    # t:1602354892
    # c:183e99f73bb1223768aa7231a836a3e98e94c03e
    # i:docs rtpproxy=2.1.1-r0
    # p:alias-of-rtpproxy=2.1.1-r0

    while True:
        entry = {}
        while (l := f.readline().decode('utf-8')) not in ['', '\n']:
            k, v = l.strip().split(':', 1)
            entry[k] = v

        if entry:
            yield entry
        else:
            break


class Dependency:
    """
    Dependency class represents apk (Alpine Package) dependency information.
    """

    type = None
    """
    :ivar: the type of the Dependency.
           e.g.
           - None: package
           - 'cmd': command
           - 'so': shared object
    """

    name = None
    """
    :ivar: the name of the Dependency.
    """

    version = None
    """
    :ivar: the version of the Dependency.
    """

    def __init__(self, item):
        try:
            self.type, self.name = item.split(':', 1)
        except (ValueError):
            self.name = item
        try:
            self.name, self.version = self.name.split('=', 1)
        except (ValueError):
            pass


def parse_deps(text):
    return [Dependency(item) for item in text.split(' ')]


def enumerate_apk_packages(base_url, os_name, os_code_name, os_arch):
    """
    Enumerate packages in an apk (Alpine Package) repository.

    :param base_url: the apk repository base URL.
    :param os_name: the name of the OS associated with the repository.
    :param os_code_name: the OS version associated with the repository.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """

    base_url = base_url.replace('$releasever', os_code_name)
    apkindex_url = os.path.join(base_url, os_arch, 'APKINDEX.tar.gz')
    print('Reading apk package metadata from ' + apkindex_url)

    with open_compressed_url(apkindex_url) as f:
        with tarfile.open(mode='r|', fileobj=f) as tf:
            index = None
            for ti in tf:
                if ti.name == 'APKINDEX':
                    index = tf.extractfile(ti)
                    break
            if index is None:
                raise RuntimeError('APKINDEX url did not contain an APKINDEX file')

            for index_entry in parse_apkindex(index):
                pkg_name, pkg_version, source_name = index_entry['P'], index_entry['V'], index_entry['o']
                pkg_filename = '%s-%s.apk' % (pkg_name, pkg_version)
                pkg_url = os.path.join(base_url, pkg_filename)
                yield PackageEntry(pkg_name, pkg_version, pkg_url, source_name=source_name)

                if 'p' in index_entry:
                    for d in parse_deps(index_entry['p']):
                        if d.type is None:
                            yield PackageEntry(d.name, pkg_version, pkg_url, source_name=source_name, binary_name=pkg_name)


def apk_base_url(base_url):
    """
    Create an enumerable cache for an apk (Alpine Package) repository.

    :param base_url: the URL of the apk repository.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_apk_packages(base_url, os_name, os_code_name, os_arch))
