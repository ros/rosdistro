#!/usr/bin/env python

from __future__ import print_function

import argparse
import sys
import yaml


def sort_yaml(yaml_file):
    data = yaml.safe_load(open(yaml_file, 'r'))
    if 'version' in data:
        print('This script does not support the new rosdistro yaml files', file=sys.stderr)
        sys.exit(1)
    sort_yaml_data(data)
    with open(yaml_file, 'w') as out_file:
        yaml.dump(data, out_file, default_flow_style=False)


def sort_yaml_data(data):
    # sort lists
    if isinstance(data, list):
        data.sort()
    # recurse into each value of a dict
    elif isinstance(data, dict):
        for k in data:
            sort_yaml_data(data[k])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Sort the .yaml file in place.')
    parser.add_argument('yaml_file', help='The .yaml file to update')
    args = parser.parse_args()
    sort_yaml(args.yaml_file)
