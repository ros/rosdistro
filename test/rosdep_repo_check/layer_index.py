# Copyright (c) 2024, Open Source Robotics Foundation
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

import json
import os

from . import open_compressed_url
from . import PackageEntry
from . import RepositoryCacheCollection


def enumerate_recipes(base_url, branch_name):
    recipes_url = os.path.join(base_url, 'recipes')
    recipes_url += f'?filter=layerbranch__branch__name:{branch_name}'
    print('Reading OpenEmbedded recipe metadata from ' + recipes_url)
    with open_compressed_url(recipes_url) as f:
        yield from json.load(f)


def enumerate_layers_by_layer_branch_id(base_url, branch_name):
    layers = dict(enumerate_layers(base_url))
    layer_branches_url = os.path.join(base_url, 'layerBranches')
    layer_branches_url += f'?filter=branch__name:{branch_name}'
    print('Reading OpenEmbedded layer branches from ' + layer_branches_url)
    with open_compressed_url(layer_branches_url) as f:
        for layer_branch in json.load(f):
            layer_branch_id = str(layer_branch.get('id', ''))
            layer_id = str(layer_branch.get('layer', ''))
            if not layer_branch_id or not layer_id:
                continue

            layer_name = layers.get(layer_id)
            if not layer_name:
                continue

            yield (layer_branch_id, layer_name)


def enumerate_layers(base_url):
    layers_url = os.path.join(base_url, 'layerItems')
    print('Reading OpenEmbedded layers from ' + layers_url)
    with open_compressed_url(layers_url) as f:
        for layer in json.load(f):
            layer_id = str(layer.get('id', ''))
            layer_name = layer.get('name')
            if not layer_id or not layer_name:
                continue
            yield (layer_id, layer_name)


def enumerate_layer_index_packages(base_url, branch_name):
    """
    Enumerate OpenEmbedded recipes in a layer index.

    :param base_url: the OpenEmbedded layer index URL.
    :param branch_name: the OpenEmbedded branch name.

    :returns: an enumeration of package entries.
    """
    layer_branches = dict(
        enumerate_layers_by_layer_branch_id(base_url, branch_name))
    for recipe in enumerate_recipes(base_url, branch_name):
        recipe_id = str(recipe.get('id', ''))
        layer_branch_id = str(recipe.get('layerbranch', ''))
        pn = recipe.get('pn')
        if not recipe_id or not layer_branch_id or not pn:
            continue

        layer = layer_branches.get(layer_branch_id)
        if not layer:
            continue

        recipe_url = os.path.join(base_url, 'recipes', recipe_id)
        pv = recipe.get('pv')
        yield PackageEntry(f'{pn}@{layer}', pv, recipe_url, pn, pn)

        provides = recipe.get('provides', '')

        for prov in provides.split():
            if not prov:
                continue
            yield PackageEntry(f'{prov}@{layer}', pv, recipe_url, pn, pn)


def layer_index_url(base_url):
    """
    Create an enumerable cache for an OpenEmbedded layer index.

    :param base_url: the URL of the layer index.

    :returns: an enumerable repository cache instance.
    """
    return RepositoryCacheCollection(
        lambda os_name, os_code_name, os_arch:
            enumerate_layer_index_packages(base_url, os_code_name))
