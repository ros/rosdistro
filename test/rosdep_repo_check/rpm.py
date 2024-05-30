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

from . import open_compressed_url
from . import PackageEntry
from . import RepositoryCacheCollection
from . import URLError


def replace_tokens(string, os_name, os_code_name, os_arch):
    """Replace RPM-specific tokens in the repository base URL."""
    for key, value in {
        '$basearch': os_arch,
        '$distname': os_name,
        '$releasever': os_code_name,
    }.items():
        string = string.replace(key, value)
    return string


def get_primary_name(repomd_url):
    """Get the URL of the 'primary' metadata from the 'repo' metadata."""
    print('Reading RPM repository metadata from ' + repomd_url)
    with open_compressed_url(repomd_url) as f:
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


def enumerate_base_urls(mirrorlist_url):
    """Get candidate RPM repository base URLs from a mirrorlist file."""
    with open_compressed_url(mirrorlist_url) as f:
        while True:
            line = f.readline().decode('utf-8')
            if not len(line):
                break
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            yield line


def enumerate_rpm_packages(base_url, os_name, os_code_name, os_arch):
    """
    Enumerate packages in an RPM repository.

    :param base_url: the RPM repository base URL.
    :param os_name: the name of the OS associated with the repository.
    :param os_code_name: the OS version associated with the repository.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """
    base_url = replace_tokens(base_url, os_name, os_code_name, os_arch)
    repomd_url = os.path.join(base_url, 'repodata', 'repomd.xml')
    primary_xml_name = get_primary_name(repomd_url)
    primary_xml_url = os.path.join(base_url, primary_xml_name)
    print('Reading RPM primary metadata from ' + primary_xml_url)
    with open_compressed_url(primary_xml_url) as f:
        tree = ElementTree.iterparse(f)
        for event, element in tree:
            if (
                element.tag != '{http://linux.duke.edu/metadata/common}package' or
                element.attrib.get('type', '') != 'rpm'
            ):
                continue
            pkg_name = None
            pkg_version = None
            pkg_src_name = None
            pkg_url = None
            pkg_provs = []
            for pkg_child in element:
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
                elif pkg_child.tag == '{http://linux.duke.edu/metadata/common}location':
                    pkg_href = pkg_child.attrib.get('href')
                    if pkg_href:
                        pkg_url = os.path.join(base_url, pkg_href)
                elif pkg_child.tag == '{http://linux.duke.edu/metadata/common}format':
                    for format_child in pkg_child:
                        if format_child.tag == '{http://linux.duke.edu/metadata/rpm}sourcerpm':
                            if format_child.text:
                                pkg_src_name = '-'.join(format_child.text.split('-')[:-2])
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
                            pkg_provs.append((provides.attrib['name'], prov_version))
            yield PackageEntry(pkg_name, pkg_version, pkg_url, pkg_src_name)
            for prov_name, prov_version in pkg_provs:
                yield PackageEntry(prov_name, prov_version, pkg_url, pkg_src_name, pkg_name)
            element.clear()


def enumerate_rpm_packages_from_mirrorlist(mirrorlist_url, os_name, os_code_name, os_arch):
    """
    Enumerate packages in an RPM repository using a mirrorlist.

    :param mirrorlist_url: the RPM repository mirrorlist file URL.
    :param os_name: the name of the OS associated with the repository.
    :param os_code_name: the OS version associated with the repository.
    :param os_arch: the system architecture associated with the repository.

    :returns: an enumeration of package entries.
    """
    mirrorlist_url = replace_tokens(mirrorlist_url, os_name, os_code_name, os_arch)
    print('Reading RPM mirrorlist from ' + mirrorlist_url)
    for base_url in enumerate_base_urls(mirrorlist_url):
        try:
            for pkg in enumerate_rpm_packages(base_url, os_name, os_code_name, os_arch):
                yield pkg
            else:
                return
        except Exception as e:
            if not isinstance(e, (
                ConnectionResetError,
                RuntimeError,
                URLError,
            )):
                raise
            print("Error reading from mirror '%s': %s" % (base_url, str(e)))
            print('Falling back to next available mirror...')
            # We may end up re-enumerating some packages, but it's better than
            # erroring out due to a connection reset...
    else:
        raise RuntimeError('All mirrors were tried')


def rpm_base_url(base_url):
    """
    Create an enumerable cache for an RPM repository.

    :param base_url: the URL of the RPM repository.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_rpm_packages(base_url, os_name, os_code_name, os_arch))


def rpm_mirrorlist_url(mirrorlist_url):
    """
    Create an enumerable cache for an RPM repository mirrorlist.

    :param mirrorlist_url: the URL of the RPM repository mirrorlist file.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_rpm_packages_from_mirrorlist(
                mirrorlist_url, os_name, os_code_name, os_arch))
