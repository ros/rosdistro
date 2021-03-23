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


def is_probably_gzip(response):
    return (response.url.endswith('.gz') or
            response.getheader('Content-Encoding') == 'gzip' or
            response.getheader('Content-Type') == 'application/x-gzip')


def open_gz_url(url, retry=2, retry_period=1, timeout=10):
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
    return GzipFile(fileobj=f, mode='rb') if is_probably_gzip(f) else f


class PackageEntry(str):

    def __new__(cls, name, version, source_name=None, binary_name=None):
        obj = str.__new__(cls, name)
        obj.name = obj
        obj.version = version
        obj.source_name = obj if source_name is None else source_name
        obj.binary_name = obj if binary_name is None else binary_name
        return obj


class RepositoryCache:

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
        while self._source_iterator:
            try:
                val = next(self._source_iterator)
                self._cache.add(val)
                yield val
            except StopIteration:
                self._source_iterator = None

    def _enumerate_packages(self):
        yield from self._cache
        yield from self._enumerate_from_source()


class RepositoryCacheCollection:

    def __init__(self, iterator):
        self._cache = {}
        self._iterator = iterator

    def enumerate_packages(self, os_name, os_code_name, os_arch):
        cache = self._cache.get((os_name, os_code_name, os_arch))
        if not cache:
            cache = RepositoryCache(self._iterator(os_name, os_code_name, os_arch))
            self._cache[(os_name, os_code_name, os_arch)] = cache
        return cache


def summarize_broken_packages(broken):
    # Group and sort by os, version, arch, key
    grouped = {}

    for os_name, os_ver, os_arch, key, package in broken:
        platform = '%s %s on %s' % (os_name, os_ver, os_arch)
        if platform not in grouped:
            grouped[platform] = set()
        grouped[platform].add('- Package %s for rosdep key %s' % (package, key))

    return '\n\n'.join(
        '* The following %d packages were not found for %s:\n%s' % (
            len(pkg_msgs), platform, '\n'.join(sorted(pkg_msgs)))
        for platform, pkg_msgs in sorted(grouped.items()))


def find_package(config, pkg_name, os_name, os_code_name, os_arch):
    if os_name not in config['package_sources']:
        return

    for os_sources in config['package_sources'][os_name]:
        if isinstance(os_sources, dict):
            sources = os_sources.get(os_code_name, [])
        else:
            sources = [os_sources]
        if not sources:
            print('WARNING: No sources for %s %s' % (os_name, os_code_name), file=sys.stderr)
        for source in sources:
            for p in [
                    p for p in source.enumerate_packages(os_name, os_code_name, os_arch)
                    if p == pkg_name]:
                return p
