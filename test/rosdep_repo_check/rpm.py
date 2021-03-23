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
from xml.etree import ElementTree

from . import open_gz_url
from . import PackageEntry
from . import RepositoryCacheCollection


def replace_tokens(string, os_name, os_code_name, os_arch):
    for key, value in {
        '$basearch': os_arch,
        '$distname': os_name,
        '$releasever': os_code_name,
    }.items():
        string = string.replace(key, value)
    return string


def get_primary_name(repomd_url):
    print('Reading RPM repository metadata from ' + repomd_url)
    with open_gz_url(repomd_url) as f:
        tree = iter(ElementTree.iterparse(f, events=('start', 'end')))
        event, root = next(tree)
        if root.tag != '{http://linux.duke.edu/metadata/repo}repomd':
            raise RuntimeError('Invalid root element in repository metadata: ' + root.tag)
        for event, root_child in tree:
            if (
                root_child.tag != '{http://linux.duke.edu/metadata/repo}data' or
                root_child.attrib.get('type', '') != 'primary'
            ):
                root.clear()
                continue
            for data_child in root_child:
                if (
                    data_child.tag != '{http://linux.duke.edu/metadata/repo}location' or
                    'href' not in data_child.attrib
                ):
                    root.clear()
                    continue
                return data_child.attrib['href']
            root.clear()
    raise RuntimeError('Failed to determine primary data file name')


def enumerate_rpm_packages(base_url, os_name, os_code_name, os_arch):
    base_url = replace_tokens(base_url, os_name, os_code_name, os_arch)
    repomd_url = os.path.join(base_url, 'repodata', 'repomd.xml')
    primary_xml_name = get_primary_name(repomd_url)
    primary_xml_url = os.path.join(base_url, primary_xml_name)
    print('Reading RPM primary metadata from ' + primary_xml_url)
    with open_gz_url(primary_xml_url) as f:
        tree = iter(ElementTree.iterparse(f, events=('start', 'end')))
        event, root = next(tree)
        if root.tag != '{http://linux.duke.edu/metadata/common}metadata':
            raise RuntimeError('Invalid root element in primary metadata: ' + root.tag)
        for event, pkg in tree:
            if (
                pkg.tag != '{http://linux.duke.edu/metadata/common}package' or
                pkg.attrib.get('type', '') != 'rpm'
            ):
                root.clear()
                continue
            pkg_name = None
            pkg_version = None
            pkg_src_name = None
            for pkg_child in pkg:
                if pkg_child.tag == '{http://linux.duke.edu/metadata/common}name':
                    pkg_name = pkg_child.text
                elif pkg_child.tag == '{http://linux.duke.edu/metadata/common}version':
                    pkg_version = pkg_child.attrib.get('ver')
                    if pkg_version:
                        pkg_epoch = pkg_child.attrib.get('epoch', '0')
                        if pkg_epoch != '0':
                            pkg_version = pkg_epoch + ':' + pkg_version
                        pkg_rel = pkg_child.attrib.get('rel')
                        if pkg_rel:
                            pkg_version = pkg_version + '-' + pkg_rel
                elif pkg_child.tag == '{http://linux.duke.edu/metadata/common}format':
                    for format_child in pkg_child:
                        if format_child.tag == '{http://linux.duke.edu/metadata/rpm}sourcerpm':
                            pkg_src_name = format_child.text
                        if format_child.tag != '{http://linux.duke.edu/metadata/rpm}provides':
                            continue
                        for provides in format_child:
                            if (
                                provides.tag != '{http://linux.duke.edu/metadata/rpm}entry' or
                                'name' not in provides.attrib
                            ):
                                continue
                            prov_version = None
                            if provides.attrib.get('flags', '') == 'EQ':
                                prov_version = provides.attrib.get('ver')
                                if prov_version:
                                    prov_epoch = provides.attrib.get('epoch', '0')
                                    if prov_epoch != '0':
                                        prov_version = prov_epoch + ':' + prov_version
                                    prov_rel = provides.attrib.get('rel')
                                    if prov_rel:
                                        prov_version = prov_version + '-' + prov_rel
                            yield PackageEntry(
                                provides.attrib['name'], prov_version, pkg_src_name, pkg_name)
            if pkg_name:
                yield PackageEntry(pkg_name, pkg_version, pkg_src_name)
            root.clear()


def rpm_base_url(base_url):
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_rpm_packages(base_url, os_name, os_code_name, os_arch))
