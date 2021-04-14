#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys
import yaml

from sort_yaml import sort_yaml_data


def add_devel_repository(yaml_file, name, vcs_type, url, version=None):
    data = yaml.safe_load(open(yaml_file, 'r'))
    if data['type'] == 'gbp':
        add_devel_repository_fuerte(yaml_file, data, name, vcs_type, url, version)
        return

    if data['type'] != 'source':
        raise RuntimeError('The passed .yaml file is neither of type "source" nor "gbp"')

    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)

    data['repositories'][name] = {
        'type': vcs_type,
        'url': url,
        'version': version,
    }
    try:
        from rosdistro.verify import _to_yaml, _yaml_header_lines
    except ImportError as e:
        raise ImportError(str(e) + ' - you need to install the latest version of python-rosdistro.')
    data = _to_yaml(data)
    data = '\n'.join(_yaml_header_lines('source')) + '\n' + data
    with open(yaml_file, 'w') as f:
        f.write(data)


def add_devel_repository_fuerte(yaml_file, data, name, vcs_type, url, version):
    if data['type'] != 'devel':
        raise RuntimeError('The passed .yaml file is not of type "devel"')
    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)
    values = {
        'type': vcs_type,
        'url': url,
    }
    if version is None and vcs_type != 'svn':
        raise RuntimeError('All repository types except SVN require a version attribute')
    if version is not None:
        if vcs_type == 'svn':
            raise RuntimeError('SVN repository must not have a version attribute but must contain the version in the URL')
    values['version'] = version
    data['repositories'][name] = values
    sort_yaml_data(data)
    with open(yaml_file, 'w') as out_file:
        yaml.dump(data, out_file, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert a repository into the .yaml file.')
    parser.add_argument('yaml_file', help='The yaml file to update')
    parser.add_argument('name', help='The unique name of the repo')
    parser.add_argument('type', help='The type of the repository (i.e. "git", "hg", "svn")')
    parser.add_argument('url', help='The url of the repository')
    parser.add_argument('version', nargs='?', help='The version')
    args = parser.parse_args()

    try:
        add_devel_repository(args.yaml_file, args.name, args.type, args.url, args.version)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)
