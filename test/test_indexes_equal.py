# Copyright (c) 2017, Open Source Robotics Foundation
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

from rosdistro import get_index

from .fold_block import Fold

INDEX_V3_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'index.yaml'))
INDEX_V4_YAML = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'index-v4.yaml'))


def test_build_caches():
    with Fold():
        print('Checking that the index.yaml and index-v4.yaml files contain '
              'the same information expect additional metadata in the v4.')
        index_v3 = get_index('file://' + os.path.abspath(INDEX_V3_YAML))
        index_v4 = get_index('file://' + os.path.abspath(INDEX_V4_YAML))

        dist_names_v3 = list(sorted(index_v3.distributions.keys()))
        dist_names_v4 = list(sorted(index_v4.distributions.keys()))
        assert dist_names_v3 == dist_names_v4, \
            'Different set of distribution names'

        for dist_name in dist_names_v3:
            dist_v3_data = index_v3.distributions[dist_name]
            dist_v4_data = index_v4.distributions[dist_name]

            for key, value in dist_v3_data.items():
                assert key in dist_v4_data, \
                    "For distribution '%s' index.yaml contains the key '%s' " \
                    "but v4 doesn't contain it" % (dist_name, key)
                assert dist_v4_data[key] == value, \
                    "For distribution '%s' both yaml files contains the key " \
                    "'%s' but with different values" % (dist_name, key)
