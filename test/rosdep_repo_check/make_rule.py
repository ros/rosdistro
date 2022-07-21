#!/usr/bin/env python3

"""
Make a rosdep rule from a given an os, release, and package name.
"""

import argparse

from typing import Dict
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple

import yaml


class Key:

    def __init__(self, *, name=None):
        # ex: 'ubuntu': ['focal', 'jammy']
        self._platforms: Dict[str, List[str]] = {}
        # ex: ('ubuntu', 'focal'): 'cmake'
        self._packages: Dict[Tuple[str, str], Optional[str]] = {}
        # Override the name of the rosdep key
        self._name = name

    def add_rule(
            self, os: str, release: str, package_name: Optional[str] = None
        ) -> None:
        os = str(os)
        release = str(release)
        if package_name:
            package_name = str(package_name)
        if os not in self._platforms.keys():
            self._platforms[os] = []
        if release not in self._platforms[os]:
            self._platforms[os].append(release)
        self._packages[(os, release)] = package_name

    def _calculate_name(self) -> Optional[str]:
        # Prioritize name of ubuntu package as the key name
        for os in ('ubuntu', 'debian'):
            if os in self._platforms.keys():
                for release in self._platforms[os]:
                    package = self._packages[(os, release)]
                    if package:
                        return package

    @property
    def name(self) -> Optional[str]:
        if not self._name:
            self._name = self._calculate_name()
        return self._name

    def as_dict(self):
        if self.name is None:
            raise ValueError('Key has no name')
        yaml_dict = {}

        for os, releases in self._platforms.items():
            if os not in yaml_dict:
                yaml_dict[os] = {}
            for release in releases:
                package = self._packages[(os, release)]
                yaml_dict[os][release] = [package] if package else None

        return {self.name: yaml_dict}


def _minimize_rules(yaml_dict, supported_versions):
    # Remove entries which are entirely null
    for key_name in list(yaml_dict.keys()):
        for os in list(yaml_dict[key_name].keys()):
            os_rules = yaml_dict[key_name][os]
            if isinstance(os_rules, dict):
                if any(os_rules.values()):
                    continue
            elif isinstance(os_rules, list):
                if any(os_rules):
                    continue
            del yaml_dict[key_name][os]
    for _, rules in yaml_dict.items():
        # Based on supported versions, convert the most recent version to '*'
        for os, release_packages in rules.items():
            if os not in supported_versions:
                continue
            latest_version = supported_versions[os][-1]
            if latest_version in release_packages:
                release_packages['*'] = release_packages[latest_version]
                del release_packages[latest_version]
                # Drop any other versions which are the same as the latest
                for release in list(release_packages.keys()):
                    if release == '*':
                        continue
                    if release_packages[release] == release_packages['*']:
                        del release_packages[release]
                # Condense iff the only version remaining is '*'
                if tuple(release_packages.keys()) == ('*',):
                    rules[os] = release_packages['*']


def _add_package_url(package_urls, os, release, url):
    if os not in package_urls.keys():
        package_urls[os] = {}
    package_urls[os][release] = url


def _represent_list(self, data):
    if all([isinstance(v, str) for v in data]):
        # This is a list of packages
        return self.represent_sequence(
            'tag:yaml.org,2002:seq', data, flow_style='block')
    return yaml.Dumper.represent_list(self, data)


def main():
    parser = argparse.ArgumentParser(description='Make a rosdep key')
    parser.add_argument(
        'os', metavar='OS',
        help='An os name (ubuntu, etc)')
    parser.add_argument(
        'release', metavar='RELEASE',
        help='An os release (focal, etc)')
    parser.add_argument(
        'package', metavar='PACKAGE',
        help='The name of the package to create a key for')

    arg = parser.parse_args()

    from .config import load_config

    cfg = load_config()

    # Add null entries for all supported platforms
    r = Key()
    for os, releases in cfg['supported_versions'].items():
        for release in releases:
            r.add_rule(os, release)

    from . import find_package
    from .config import load_config
    from .suggest import make_suggestion

    from urllib.error import HTTPError

    # Make sure requested package exists
    arch = cfg['supported_arches'][arg.os][0]
    suggestion = find_package(cfg, arg.package, arg.os, arg.release, arch)
    if not suggestion:
        raise RuntimeError(
            f'Did not find package {arg.package} in {arg.os} {arg.release}')

    r.add_rule(arg.os, arg.release, suggestion.binary_name)

    # ex: 'ubuntu': {'focal': 'https://...'}
    package_urls: Dict[str, Dict[str, str]] = {}
    _add_package_url(package_urls, arg.os, arg.release, suggestion.url)

    # Look up packages for all platforms
    for os, releases in cfg['supported_versions'].items():
        try:
            suggestion = make_suggestion(cfg, arg.package, os)
        except HTTPError:
            pass
        else:
            if suggestion is None:
                continue
            os_pkg = suggestion.binary_name
            arch = cfg['supported_arches'][os][0]
            for release in releases:
                try:
                    suggestion = find_package(cfg, os_pkg, os, release, arch)
                except HTTPError:
                    pass
                else:
                    if suggestion is None:
                        continue
                    r.add_rule(os, release, suggestion.binary_name)
                    _add_package_url(
                        package_urls, os, release, suggestion.url)

    # Make lists use block style if they contain only strings
    yaml.Dumper.add_representer(list, _represent_list)

    print('-' * 25)
    print('# URLs  for packages')
    for os, release_urls in sorted(package_urls.items()):
        print(f'* {os}')
        for release, url in sorted(release_urls.items()):
            print(f'  * [{release}]({url})')
    print('-' * 25)
    print('# Non-minimized rules')
    yaml_dict = r.as_dict()
    print(yaml.dump(yaml_dict))
    print('-' * 25)
    print('# Minimized rules')
    _minimize_rules(yaml_dict, cfg['supported_versions'])
    print(yaml.dump(yaml_dict))


if __name__ == '__main__':
    main()
