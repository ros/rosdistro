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

from . import find_package


def verify_rules(config, rules_to_check, all_rules, include_found=False):
    """
    Verify rosdep rules for supported platforms.

    For all platforms supported in the YAML configuration, verify that the
    repositories contain the packages listed in the rosdep rules.

    :param config: the parsed YAML configuration.
    :param rules_to_check: rosdep rules to be checked.
    :param all_rules: full rosdep rules to check for individual version rules.
    :param include_found: in addition to missing rules, also yield those found.

    :returns: a tuple of:
        - OS name
        - OS version
        - OS architecture
        - rosdep key
        - package name
        - corresponding package entry, if found
    """
    for key, rules in rules_to_check.items():
        for os_name, os_rules in rules.items():
            if os_name not in config['package_sources']:
                continue
            packages_to_check = {}
            if not isinstance(os_rules, dict):
                for os_ver in config['supported_versions'].get(os_name, ()):
                    packages_to_check[os_ver] = os_rules
            else:
                packages_to_check = os_rules
                if '*' in os_rules:
                    for os_ver in config['supported_versions'].get(os_name, ()):
                        if os_ver not in all_rules[key][os_name]:
                            packages_to_check.setdefault(os_ver, os_rules['*'])
                    del packages_to_check['*']
            for os_ver, packages in packages_to_check.items():
                if os_ver not in config['supported_versions'].get(os_name, ()):
                    continue
                if isinstance(packages, dict) and \
                        tuple(packages.keys()) == ('packages',):
                    packages = packages['packages']
                if not isinstance(packages, list):
                    # Probably a dict specifying the key type, which is not
                    # currently supported
                    continue
                for package in packages or []:
                    for needle, haystack in config['name_replacements'].get(
                            os_name, {}).get(os_ver, {}).items():
                        package = package.replace(needle, haystack)
                    for os_arch in config['supported_arches'][os_name]:
                        res = find_package(config, package, os_name, os_ver, os_arch)
                        if not res or include_found:
                            yield (os_name, os_ver, os_arch, key, package, res)
