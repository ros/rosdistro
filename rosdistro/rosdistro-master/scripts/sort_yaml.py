#!/usr/bin/env python

import argparse
import yaml


def sort_yaml(yaml_file):
    data = yaml.load(open(yaml_file, 'r'))
    sort_yaml_data(data)
    yaml.dump(data, file(yaml_file, 'w'), default_flow_style=False)


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
