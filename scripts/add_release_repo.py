#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys
import yaml

from sort_yaml import sort_yaml_data


def add_release_repository(yaml_file, name, url, version):
    data = yaml.safe_load(open(yaml_file, 'r'))
    if data['type'] == 'gbp':
        add_release_repository_fuerte(yaml_file, data, name, url, version)
        return

    raise RuntimeError('The passed .yaml file is not of type "gbp" and it is not supported for Groovy or newer')


def add_release_repository_fuerte(yaml_file, data, name, url, version):
    if name in data['repositories']:
        raise RuntimeError('Repository with name "%s" is already in the .yaml file' % name)
    data['repositories'][name] = {
        'url': url,
        'version': version,
    }
    sort_yaml_data(data)
    with open(yaml_file, 'w') as out_file:
        yaml.dump(data, out_file, default_flow_style=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert a git-buildpackage repository into the .yaml file.')
    parser.add_argument('yaml_file', help='The yaml file to update')
    parser.add_argument('name', help='The unique name of the repo')
    parser.add_argument('url', help='The url of the GBP repository')
    parser.add_argument('version', help='The version')
    args = parser.parse_args()

    try:
        add_release_repository(args.yaml_file, args.name, args.url, args.version)
    except Exception as e:
        print(str(e), file=sys.stderr)
        exit(1)
