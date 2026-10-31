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

import gzip
from io import BytesIO
import lzma
from unittest.mock import Mock

import pytest
from zstandard import ZstdCompressor

from . import open_compressed_url
from . import URLError


class Response(BytesIO):

    def __init__(self, data, url, content_length=None):
        super().__init__(data)
        self.url = url
        self.content_length = len(data) if content_length is None else content_length

    def getheader(self, name):
        return str(self.content_length) if name == 'Content-Length' else None


@pytest.mark.parametrize('suffix,compress', [
    ('', lambda data: data),
    ('.gz', gzip.compress),
    ('.xz', lzma.compress),
    ('.zst', ZstdCompressor().compress),
])
def test_download_outlives_http_connection(monkeypatch, suffix, compress):
    data = b'repository metadata' * 1000
    url = 'https://example.com/Packages' + suffix
    response = Response(compress(data), url)
    monkeypatch.setattr('test.rosdep_repo_check.urlopen', Mock(return_value=response))

    with open_compressed_url(url) as stream:
        # Simulate the remote connection expiring before enumeration resumes.
        response.close()
        assert stream.read() == data


def test_incomplete_download_is_retried(monkeypatch):
    url = 'https://example.com/Packages'
    incomplete = Response(b'partial', url, content_length=100)
    complete = Response(b'complete repository metadata', url)
    urlopen = Mock(side_effect=[incomplete, complete])
    monkeypatch.setattr('test.rosdep_repo_check.urlopen', urlopen)

    with open_compressed_url(url, retry=1, retry_period=0) as stream:
        assert stream.read() == b'complete repository metadata'
    assert urlopen.call_count == 2
    assert incomplete.closed
    assert complete.closed


def test_incomplete_download_exhausts_retries(monkeypatch):
    url = 'https://example.com/Packages'
    response = Response(b'partial', url, content_length=100)
    monkeypatch.setattr('test.rosdep_repo_check.urlopen', Mock(return_value=response))

    with pytest.raises(URLError, match='bytes read'):
        open_compressed_url(url, retry=0)
    assert response.closed


def test_interrupted_download_is_retried(monkeypatch):
    url = 'https://example.com/Packages'
    interrupted = Response(b'', url)
    interrupted.read = Mock(side_effect=ConnectionResetError('connection reset'))
    complete = Response(b'complete repository metadata', url)
    urlopen = Mock(side_effect=[interrupted, complete])
    monkeypatch.setattr('test.rosdep_repo_check.urlopen', urlopen)

    with open_compressed_url(url, retry=1, retry_period=0) as stream:
        assert stream.read() == b'complete repository metadata'
    assert urlopen.call_count == 2
    assert interrupted.closed
