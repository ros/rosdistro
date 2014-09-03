#!/usr/bin/env python


import subprocess
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor
import pprint
import re

DIFF_TARGET = 'origin/master'
FILE_TARGET = '../indigo/distribution.yaml'


def detect_lines(diffstr):
    diff_nums = []
    reexp = re.compile('@@(.*)@@')
    matches = reexp.findall(diffstr)
    for m in matches:
        # print m
        linepair = m.strip().split(' ')
        new_lines = linepair[1].lstrip('+').split(',')
        if len(new_lines) == 1:
            diff_nums.append(int(new_lines[0]))
            continue

        start = int(new_lines[0])
        end = start + int(new_lines[1])

        diff_nums.extend(range(start, end))
    return diff_nums


def check_git_remote_exists(url, version):
    """ Check if the remote exists and has the branch version """
    cmd = ('git ls-remote %s --heads ./.' % url).split()

    try:
        output = subprocess.check_output(cmd)
    except:
        return False
    if not version:
        # If the above passed assume the default exists
        return True

    if 'refs/heads/%s' % version in output:
        return True
    return False


def check_source_repo_entry_for_errors(source):
    if source['type'] != 'git':
        print("Cannot verify remote of type[%s] from line [%s] skipping."
              % (source['type'], source['__line__']))
        return None
    version = source['version'] if source['version'] else None
    if not check_git_remote_exists(source['url'], version):
        return ("Could not validate repository with url %s and version %s from"
                " entry at line %s" % (source['url'],
                                       version,
                                       source['__line__']))
    return None


def check_repo_for_errors(repo):
    errors = []
    if 'source' in repo:
        source_errors = check_source_repo_entry_for_errors(repo['source'])
        if source_errors:
            errors.append("Could not validate source entry for repo %s with error %s" %
                          (repo['repo'], source_errors))
    if 'doc' in repo:
        source_errors = check_source_repo_entry_for_errors(repo['doc'])
        if source_errors:
            errors.append("Could not validate doc entry for repo %s with error %s" %
                          (repo['repo'], source_errors))
    return errors


def main():
    cmd = ('git diff --unified=0 %s' % DIFF_TARGET).split()
    diff = subprocess.check_output(cmd)
    print("output", diff)

    diffed_lines = detect_lines(diff)
    print("Diff lines %s" % diffed_lines)

    d = open(FILE_TARGET).read()
    loader = yaml.Loader(d)

    def compose_node(parent, index):
        # the line number where the previous token has ended (plus empty lines)
        line = loader.line
        node = Composer.compose_node(loader, parent, index)
        node.__line__ = line + 1
        return node

    def construct_mapping(node, deep=False):
        mapping = Constructor.construct_mapping(loader, node, deep=deep)
        mapping['__line__'] = node.__line__
        return mapping
    loader.compose_node = compose_node
    loader.construct_mapping = construct_mapping
    data = loader.get_single_data()

    repos = data['repositories']

    changed_repos = {}

    for dl in diffed_lines:
        match = None
        for name, values in repos.items():
            if name == '__line__':
                continue
            if not isinstance(values, dict):
                print("not a dict %s %s" % (name, values))
                continue
            # print("comparing to repo %s values %s" % (name, values))
            if values['__line__'] < dl:
                if match and match['__line__'] > values['__line__']:
                    continue
                match = values
                match['repo'] = name
        if match:
            changed_repos[match['repo']] = match

    print("changed repos are:")
    pprint.pprint(changed_repos)

    detected_errors = []
    for n, r in changed_repos.items():
        detected_errors.extend(check_repo_for_errors(r))
    for e in detected_errors:
        print(e)

main()
