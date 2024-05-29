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

from gzip import GzipFile
from lzma import LZMAFile
import socket
import sys
import time
try:
    from urllib.error import HTTPError
    from urllib.error import URLError
    from urllib.request import Request
    from urllib.request import urlopen
except ImportError:
    from urllib2 import HTTPError
    from urllib2 import Request
    from urllib2 import URLError
    from urllib2 import urlopen


def fmt_os(os_name, os_code_name):
    return (os_name + ' ' + os_code_name) if os_code_name else os_name


def is_probably_gzip(response):
    """
    Determine if a urllib response is likely gzip'd.

    :param response: the urllib response
    """
    return (response.url.endswith('.gz') or
            response.getheader('Content-Encoding') == 'gzip' or
            response.getheader('Content-Type') == 'application/x-gzip')


def is_probably_lzma(response):
    """
    Determine if a urllib response is likely lzma'd.

    :param response: the urllib response
    """
    return (response.url.endswith('.xz') or
            response.getheader('Content-Encoding') == 'xz' or
            response.getheader('Content-Type') == 'application/x-xz')


def open_gz_url(url, retry=2, retry_period=1, timeout=10):
    return open_compressed_url(url, retry, retry_period, timeout)

def open_compressed_url(url, retry=2, retry_period=1, timeout=10):
    """
    Open a URL to a possibly compressed file.

    :param url: URL to the file.
    :param retry: number of times to re-attempt the download.
    :param retry_period: number of seconds to wait between retry attempts.
    :param timeout: number of seconds to wait for the remote host to respond.

    :returns: file-like object for streaming file data.
    """
    request = Request(url, headers={'Accept-Encoding': 'gzip'})
    try:
        f = urlopen(request, timeout=timeout)
    except HTTPError as e:
        if e.code == 503 and retry:
            time.sleep(retry_period)
            return open_gz_url(
                url, retry=retry - 1, retry_period=retry_period,
                timeout=timeout)
        e.msg += ' (%s)' % url
        raise
    except URLError as e:
        if isinstance(e.reason, socket.timeout) and retry:
            time.sleep(retry_period)
            return open_gz_url(
                url, retry=retry - 1, retry_period=retry_period,
                timeout=timeout)
        raise URLError(str(e) + ' (%s)' % url)
    if is_probably_gzip(f):
        return GzipFile(fileobj=f, mode='rb')
    elif is_probably_lzma(f):
        return LZMAFile(f, mode='rb')
    return f


class PackageEntry(str):
    """Lightweight data bag for information about an entry in a repository."""

    __slots__ = ('name', 'version', 'url', 'source_name', 'binary_name')

    def __new__(cls, name, version, url, source_name=None, binary_name=None):
        obj = str.__new__(cls, name)
        obj.name = obj
        obj.version = version
        obj.url = url
        obj.source_name = obj if source_name is None else source_name
        obj.binary_name = obj if binary_name is None else binary_name
        return obj


class RepositoryCache:
    """
    A cache of packages in a repository.

    This class acts as a cache and abstraction layer for the underlying
    platform-specific package enumeration function. It exposes progressive
    methods for testing if a package is present and also enumeration that
    can be performed multiple times without querying the source multiple
    times.
    """

    def __init__(self, iterator):
        self._cache = set()
        self._source_iterator = iterator

    def __iter__(self):
        return self._enumerate_packages()

    def __contains__(self, needle):
        if needle in self._cache:
            return True
        for pkg in self._enumerate_from_source():
            if pkg == needle:
                return True

        return False

    def _enumerate_from_source(self):
        """
        Enumerate packages directly from the source function.

        When the source has no more packages to yield, this function will also
        no longer yield any packages. As this function yields packages, they
        are added to the cache.
        """
        while self._source_iterator:
            try:
                val = next(self._source_iterator)
                self._cache.add(val)
                yield val
            except StopIteration:
                self._source_iterator = None

    def _enumerate_packages(self):
        """
        Enumerate all of the packages in the repository.

        Begin by enumerating any previously enumerated and cached packages, then
        attempt to enumerate any addition packages directly from the source.
        """
        yield from self._cache
        yield from self._enumerate_from_source()


class RepositoryCacheCollection:
    """
    A collection of individual repository caches.

    This class represents a collection of individual repositories for each
    OS, version, and arch, which are all associated with the same basic URL.
    It will create repository caches as necessary to meet enumeration
    requests, and will maintain the caches until the instance is deleted.
    """

    def __init__(self, iterator):
        self._cache = {}
        self._iterator = iterator

    def enumerate_packages(self, os_name, os_code_name, os_arch):
        """
        Enumerate packages in this repository collection for the given platform.

        :param os_name: the name of the OS associated with the packages.
        :param os_code_name: the OS version associated with the packages.
        :param os_arch: the system architecture associated with the packages.

        :returns: An enumerable cache of the packages.
        """
        cache = self._cache.get((os_name, os_code_name, os_arch))
        if not cache:
            cache = RepositoryCache(self._iterator(os_name, os_code_name, os_arch))
            self._cache[(os_name, os_code_name, os_arch)] = cache
        return cache


def summarize_broken_packages(broken):
    """
    Create human-readable summary regarding missing packages.

    :param broken: tuples with information about the broken packages.

    :returns: the human-readable summary.
    """
    # Group and sort by os, version, arch, key
    grouped = {}

    for os_name, os_ver, os_arch, key, package, _ in broken:
        platform = '%s on %s' % (fmt_os(os_name, os_ver), os_arch)
        if platform not in grouped:
            grouped[platform] = set()
        grouped[platform].add('- Package %s for rosdep key %s' % (package, key))

    return '\n\n'.join(
        '* The following %d packages were not found for %s:\n%s' % (
            len(pkg_msgs), platform, '\n'.join(sorted(pkg_msgs)))
        for platform, pkg_msgs in sorted(grouped.items()))


def find_package(config, pkg_name, os_name, os_code_name, os_arch):
    """
    Find a package by name for the given platform.

    :param config: the parsed YAML configuration.
    :param pkg_name: the name of the package to be found.
    :param os_name: the name of the OS associated with the package.
    :param os_code_name: the OS version associated with the package.
    :param os_arch: the system architecture associated with the package.

    :returns: the parsed package entry, or None if no package was found.
    """
    if os_name not in config['package_sources']:
        return

    for os_sources in config['package_sources'][os_name]:
        if isinstance(os_sources, dict):
            sources = os_sources.get(os_code_name, [])
        else:
            sources = [os_sources]
        if not sources:
            print(
                'WARNING: No sources for %s' % (fmt_os(os_name, os_code_name)),
                 file=sys.stderr)
        for source in sources:
            for p in source.enumerate_packages(os_name, os_code_name, os_arch):
                if p == pkg_name:
                    return p


def get_package_link(config, pkg, os_name, os_code_name, os_arch):
    """
    Get an informational link about a package.

    This function uses the package_dashboards configuration to attempt to create
    a URL to an information page regarding a package. If it is unsuccessful, the
    URL to the package itself is returned.

    :param config: the parsed YAML configuration.
    :param pkg: the parsed package entry.
    :param os_name: the name of the OS associated with the package.
    :param os_code_name: the OS version associated with the package.
    :param os_arch: the system architecture associated with the package.

    :returns: a URL to a dashboard or package file.
    """
    for dashboard in config.get('package_dashboards', ()):
        match = dashboard['pattern'].match(pkg.url)
        if match:
            return match.expand(dashboard['url']).format_map({
                'binary_name': pkg.binary_name,
                'name': pkg.name,
                'os_arch': os_arch,
                'os_code_name': os_code_name,
                'os_name': os_name,
                'source_name': pkg.source_name,
                'url': pkg.url,
                'version': pkg.version,
            })

    # No configured dashboard - fall back to package URL
    return pkg.url
