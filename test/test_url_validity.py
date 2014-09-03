#!/usr/bin/env python


from io import BytesIO
import subprocess
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor
import pprint
import sys
import unittest

import unidiff

DIFF_TARGET = 'origin/master'
TARGET_FILES = ['hydro/distribution.yaml',
                'indigo/distribution.yaml']


def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    io = BytesIO(diffstr)
    udiff = unidiff.parser.parse_unidiff(io)
    for file in udiff:
        target_lines = []
        # if file.path in TARGET_FILES:
        for hunk in file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[file.path] = target_lines
    return resultant_lines


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
                " entry at line '''%s'''" % (source['url'],
                                             version,
                                             source['__line__']))
    return None


def check_repo_for_errors(repo):
    errors = []
    if 'source' in repo:
        source_errors = check_source_repo_entry_for_errors(repo['source'])
        if source_errors:
            errors.append("Could not validate source entry for repo %s with error [[[%s]]]" %
                          (repo['repo'], source_errors))
    if 'doc' in repo:
        source_errors = check_source_repo_entry_for_errors(repo['doc'])
        if source_errors:
            errors.append("Could not validate doc entry for repo %s with error [[[%s]]]" %
                          (repo['repo'], source_errors))
    return errors


def load_yaml_with_lines(filename):
    d = open(filename).read()
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
    return data


def isolate_yaml_snippets_from_line_numbers(yaml_dict, line_numbers):
    changed_repos = {}

    for dl in line_numbers:
        match = None
        for name, values in yaml_dict.items():
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
    return changed_repos


def main():
    cmd = ('git diff --unified=0 %s' % DIFF_TARGET).split()
    diff = subprocess.check_output(cmd)
    # print("output", diff)

    diffed_lines = detect_lines(diff)
    # print("Diff lines %s" % diffed_lines)

    detected_errors = []

    for path, lines in diffed_lines.items():
        if path not in TARGET_FILES:
            print("not verifying diff of file %s" % path)
            continue

        data = load_yaml_with_lines(path)

        repos = data['repositories']

        changed_repos = isolate_yaml_snippets_from_line_numbers(repos, lines)

        # print("In file: %s Changed repos are:" % path)
        # pprint.pprint(changed_repos)

        for n, r in changed_repos.items():
            errors = check_repo_for_errors(r)
            detected_errors.extend(["In file '''%s''': "
                                    % path + e for e in errors])
    for e in detected_errors:
        print("ERROR: %s" % e)
    return detected_errors


class TestUruValidity(unittest.TestCase):

    def test_function(self):
        detected_errors = main()
        self.assertFalse(detected_errors)

if __name__ == "__main__":
    detected_errors = main()
    if not detected_errors:
        sys.exit(0)
    sys.exit(1)
