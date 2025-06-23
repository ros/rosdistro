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
import re
import yaml

from .apk import apk_base_url
from .deb import deb_base_url
from .layer_index import layer_index_url
from .pacman import pacman_base_url
from .rpm import rpm_base_url
from .rpm import rpm_mirrorlist_url


DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'config.yaml')


def load_apk_base_url(loader, node):
    return apk_base_url(node.value)


def load_deb_base_url(loader, node):
    base_url, comp = node.value.rsplit(' ', 1)
    return deb_base_url(base_url, comp)


def load_layer_index_url(loader, node):
    return layer_index_url(node.value)


def load_pacman_base_url(loader, node):
    base_url, repo_name = node.value.rsplit(' ', 1)
    return pacman_base_url(base_url, repo_name)


def load_rpm_base_url(loader, node):
    return rpm_base_url(node.value)


def load_rpm_mirrorlist_url(loader, node):
    return rpm_mirrorlist_url(node.value)


def load_regex(loader, node):
    return re.compile(node.value)


yaml.add_constructor(
    u'!apk_base_url', load_apk_base_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!deb_base_url', load_deb_base_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!layer_index_url', load_layer_index_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!pacman_base_url', load_pacman_base_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!rpm_base_url', load_rpm_base_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!rpm_mirrorlist_url', load_rpm_mirrorlist_url, Loader=yaml.SafeLoader)
yaml.add_constructor(
    u'!regular_expression', load_regex, Loader=yaml.SafeLoader)


def load_config(path=None):
    with open(path or DEFAULT_CONFIG_PATH) as f:
        return yaml.safe_load(f)
