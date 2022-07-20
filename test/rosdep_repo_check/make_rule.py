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

import rosdistro

import yaml


def active_distros(index: rosdistro.index.Index) -> Sequence[str]:
    distros = []
    for distro_name, metadata in index.distributions.items():
        if 'active' == metadata['distribution_status']:
            distros.append(distro_name)
    return tuple(distros)


def get_index() -> rosdistro.index.Index:
    return rosdistro.get_index(rosdistro.get_index_url())


def release_platforms(
        index: rosdistro.index.Index,
        distro_names: Sequence[str]
    ) -> Dict[str, Sequence[str]]:

    platforms = {}
    for distro in distro_names:
        for distro_file in rosdistro.get_distribution_files(index, distro):
            for os, releases in distro_file.release_platforms.items():
                if os not in platforms:
                    platforms[os] = releases
                else:
                    for release in releases:
                        if release not in platforms[os]:
                            platforms[os].append(release)
    return platforms



class Rule:

    def __init__(self, *, key=None):
        # ex: 'ubuntu': ['focal', 'jammy']
        self._platforms: Dict[str, List[str]] = {}
        # ex: ('ubuntu', 'focal'): 'cmake'
        self._packages: Dict[Tuple[str, str], Optional[str]] = {}
        # Override the key of the rosdep rule
        self._key = key

    def set_package_for_platform(
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

    def _calculate_key(self) -> Optional[str]:
        # Prioritize name of ubuntu package as the key name
        for os in ('ubuntu', 'debian'):
            if os in self._platforms.keys():
                for release in self._platforms[os]:
                    package = self._packages[(os, release)]
                    if package:
                        return package

    @property
    def key(self) -> Optional[str]:
        if not self._key:
            self._key = self._calculate_key()
        return self._key

    def as_dict(self, minimal=True):
        if self.key is None:
            raise ValueError('Rule has no key')
        yaml_dict = {}

        # First pass, put all the data in
        for os, releases in self._platforms.items():
            if os not in yaml_dict:
                yaml_dict[os] = {}
            for release in releases:
                yaml_dict[os][release] = [self._packages[(os, release)]]

        # Second pass, minimize keys
        if minimal:
            for os, release_packages in yaml_dict.items():
                package_names = set([l[0] for l in release_packages.values()])
                if len(package_names) == 1:
                    # All releases have the same package name
                    yaml_dict[os] = [package_names.pop()]
                elif len(package_names) == 2 and None in package_names:
                    # Not all releases have the package.
                    # The ones that do have the same name.
                    # This assumes releases without the package are older, and
                    # may be the wrong thing to do if a distro stopped
                    # releasing a package.
                    package_name = [n for n in package_names if n][0]
                    new_os_dict = {'*': [package_name]}
                    for release, package in release_packages.items():
                        if package is None:
                            new_os_dict[release] = None
                    yaml_dict[os] = new_os_dict
    
        return {self.key: yaml_dict}


def _add_package_url(package_urls, os, release, url):
    if os not in package_urls.keys():
        package_urls[os] = {}
    package_urls[os][release] = url


def _represent_list(self, data):
    if all([isinstance(v, str) for v in data]):
        # This is a list of packages
        return self.represent_sequence(
            'tag:yaml.org,2002:seq', data, flow_style='block')
    return yaml.Dumper.represent_list(data)


def main():
    parser = argparse.ArgumentParser(description='Make a rosdep rule')
    parser.add_argument(
        'os', metavar='OS',
        help='An os name (ubuntu, etc)')
    parser.add_argument(
        'release', metavar='RELEASE',
        help='An os release (focal, etc)')
    parser.add_argument(
        'package', metavar='PACKAGE',
        help='The name of the package to create a rule for')

    arg = parser.parse_args()

    from .config import load_config

    cfg = load_config()

    index = get_index()
    platforms = release_platforms(index, active_distros(index))

    r = Rule()
    for os, releases in platforms.items():
        for release in releases:
            r.set_package_for_platform(os, release)

    from . import find_package
    from .config import load_config
    from .suggest import make_suggestion

    from urllib.error import HTTPError

    # Make sure requested package exists
    arch = cfg['supported_arches'][arg.os][0]
    try:
        suggestion = find_package(cfg, arg.package, arg.os, arg.release, arch)
    except HTTPError:
        pass
    if not suggestion:
        raise RuntimeError(
            f'Did not find package {arg.package} in {arg.os} {arg.release}')

    r.set_package_for_platform(arg.os, arg.release, suggestion.binary_name)

    # ex: 'ubuntu': {'focal': 'https://...'}
    package_urls: Dict[str, Dict[str, str]] = {}
    _add_package_url(package_urls, arg.os, arg.release, suggestion.url)

    # Look up packages for all platforms
    # Assumes cfg['supported_versions'] includes all active platforms
    for os, releases in cfg['supported_versions'].items():
        try:
            suggestion = make_suggestion(cfg, arg.package, os)
        except HTTPError:
            pass
        if suggestion:
            for release in releases:
                try:
                    suggestion = find_package(
                        cfg, arg.package, os, release, arch)
                except HTTPError:
                    pass
                if suggestion:
                    pkg = suggestion.binary_name
                    r.set_package_for_platform(os, release, pkg)
                    _add_package_url(package_urls, os, release, suggestion.url)

    # Make lists use block style if they contain only strings
    yaml.Dumper.add_representer(list, _represent_list)

    print('-' * 25)
    print('# URLs  for packages')
    for os, release_urls in sorted(package_urls.items()):
        print(f'* {os}')
        for release, url in sorted(release_urls.items()):
            print(f'  * [{release}]({url})')
    print('-' * 25)
    print('# Non-minimized rule')
    print(yaml.dump(r.as_dict(minimal=False)))
    print('-' * 25)
    print('# Minimized rule')
    print(yaml.dump(r.as_dict()))


if __name__ == '__main__':
    main()
