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

import yaml


class AnnotatedSafeLoader(yaml.SafeLoader):
    """
    YAML loader that adds '__line__' attributes to some of the parsed data.

    This extension of the PyYAML SafeLoader replaces some basic types with
    derived types that include a '__line__' attribute to determine where
    the deserialized data can be found in the YAML file it was parsed from.
    """

    class AnnotatedDict(dict):

        __slots__ = ('__line__',)

        def __init__(self, *args, **kwargs):
            return super().__init__(*args, **kwargs)

    class AnnotatedList(list):

        __slots__ = ('__line__',)

        def __init__(self, *args, **kwargs):
            return super().__init__(*args, **kwargs)

    class AnnotatedStr(str):

        __slots__ = ('__line__',)

        def __new__(cls, *args, **kwargs):
            return str.__new__(cls, *args, **kwargs)

    def compose_node(self, parent, index):
        line = self.line
        node = super().compose_node(parent, index)
        node.__line__ = line + 1
        return node

    def construct_annotated_map(self, node):
        data = AnnotatedSafeLoader.AnnotatedDict()
        data.__line__ = node.__line__
        yield data
        value = self.construct_mapping(node)
        data.update(value)

    def construct_annotated_seq(self, node):
        data = AnnotatedSafeLoader.AnnotatedList()
        data.__line__ = node.__line__
        yield data
        data.extend(self.construct_sequence(node))

    def construct_annotated_str(self, node):
        data = self.construct_yaml_str(node)
        data = AnnotatedSafeLoader.AnnotatedStr(data)
        data.__line__ = node.__line__
        return data


AnnotatedSafeLoader.add_constructor(
    'tag:yaml.org,2002:map', AnnotatedSafeLoader.construct_annotated_map)
AnnotatedSafeLoader.add_constructor(
    'tag:yaml.org,2002:seq', AnnotatedSafeLoader.construct_annotated_seq)
AnnotatedSafeLoader.add_constructor(
    'tag:yaml.org,2002:str', AnnotatedSafeLoader.construct_annotated_str)


def merge_dict(base, to_add):
    """Merge two mappings, overwriting the first mapping with data from the second."""
    for k, v in to_add.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            merge_dict(base[k], v)
        else:
            base[k] = v


def isolate_yaml_snippets_from_line_numbers(yaml_dict, line_numbers):
    """
    Create a mapping that contains data parsed from particular lines of the source file.

    This function preserves the ancestry of a nested mapping even if those lines are not
    specifically requested.

    :param yaml_dict: a mapping parsed using the AnnotatedSafeLoader.
    :param line_numbers: a collection of line numbers to include in the isolated snippets.

    :returns: a subset of the original data based on the given line numbers.
    """
    matches = {}

    for dl in line_numbers:
        for name, values in reversed(yaml_dict.items()):
            if isinstance(values, AnnotatedSafeLoader.AnnotatedDict):
                if values.__line__ <= dl:
                    merge_dict(matches,
                               {name: isolate_yaml_snippets_from_line_numbers(values, [dl])})
                    break
            elif isinstance(values, AnnotatedSafeLoader.AnnotatedList):
                if values.__line__ <= dl:
                    matches[name] = values
                    break
    return matches
