#!/usr/bin/env python

from __future__ import print_function


try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import os
import subprocess
import sys
import unittest
from urlparse import urlparse

import rosdistro
from scripts import eol_distro_names
import unidiff
import yaml
from yaml.composer import Composer
from yaml.constructor import Constructor

from .fold_block import Fold

# for commented debugging code below
# import pprint

DIFF_TARGET = 'origin/master'


TARGET_FILE_BLACKLIST = []


def get_all_distribution_filenames(url=None):
    if not url:
        url = rosdistro.get_index_url()
    distribution_filenames = []
    i = rosdistro.get_index(url)
    for d in i.distributions.values():
        for f in d['distribution']:
            dpath = os.path.abspath(urlparse(f).path)
            distribution_filenames.append(dpath)
    return distribution_filenames


def get_eol_distribution_filenames(url=None):
    if not url:
        url = rosdistro.get_index_url()
    distribution_filenames = []
    i = rosdistro.get_index(url)
    for d_name, d in i.distributions.items():
        if d_name in eol_distro_names:
            for f in d['distribution']:
                dpath = os.path.abspath(urlparse(f).path)
                distribution_filenames.append(dpath)
    return distribution_filenames


def detect_lines(diffstr):
    """Take a diff string and return a dict of
    files with line numbers changed"""
    resultant_lines = {}
    # diffstr is already utf-8 encoded
    io = StringIO(diffstr)
    # Force utf-8 re: https://github.com/ros/rosdistro/issues/6637
    encoding = 'utf-8'
    udiff = unidiff.PatchSet(io, encoding)
    for file in udiff:
        target_lines = []
        # if file.path in TARGET_FILES:
        for hunk in file:
            target_lines += range(hunk.target_start,
                                  hunk.target_start + hunk.target_length)
        resultant_lines[file.path] = target_lines
    return resultant_lines


def check_git_remote_exists(url, version, tags_valid=False):
    """ Check if the remote exists and has the branch version.
    If tags_valid is True query tags as well as branches """
    cmd = ('git ls-remote %s refs/heads/*' % url).split()

    try:
        output = subprocess.check_output(cmd)
    except:
        return False
    if not version:
        # If the above passed assume the default exists
        return True

    if 'refs/heads/%s' % version in output:
        return True

    # If tags are valid. query for all tags and test for version
    if not tags_valid:
        return False
    cmd = ('git ls-remote %s refs/tags/*' % url).split()

    try:
        output = subprocess.check_output(cmd)
    except:
        return False

    if 'refs/tags/%s' % version in output:
        return True
    return False


def check_source_repo_entry_for_errors(source, tags_valid=False):
    if source['type'] != 'git':
        print("Cannot verify remote of type[%s] from line [%s] skipping."
              % (source['type'], source['__line__']))
        return None

    version = source['version'] if source['version'] else None
    if not check_git_remote_exists(source['url'], version, tags_valid):
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
        source_errors = check_source_repo_entry_for_errors(repo['doc'], tags_valid=True)
        if source_errors:
            errors.append("Could not validate doc entry for repo %s with error [[[%s]]]" %
                          (repo['repo'], source_errors))
    return errors


def detect_post_eol_release(n, repo, lines):
    errors = []
    if 'release' in repo:
        release_element = repo['release']
        start_line = release_element['__line__']
        end_line = start_line
        if 'tags' not in release_element:
            print('Missing tags element in release section skipping')
            return []
        # There are 3 lines beyond the tags line. The tag contents as well as
        # the url and version number
        end_line = release_element['tags']['__line__'] + 3
        matching_lines = [l for l in lines if l >= start_line and l <= end_line]
        if matching_lines:
            errors.append("There is a change to a release section of an EOLed "
                          "distribution. Lines: %s" % matching_lines)
    if 'doc' in repo:
        doc_element = repo['doc']
        start_line = doc_element['__line__']
        end_line = start_line + 3
        # There are 3 lines beyond the tags line. The tag contents as well as
        # the url and version number
        matching_lines = [l for l in lines if l >= start_line and l <= end_line]
        if matching_lines:
            errors.append("There is a change to a doc section of an EOLed "
                          "distribution. Lines: %s" % matching_lines)

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
            if values['__line__'] <= dl:
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
        directory = os.path.join(os.path.dirname(__file__), '..')
        url = 'file://%s/index.yaml' % directory
        path = os.path.abspath(path)
        if path not in get_all_distribution_filenames(url):
            # print("not verifying diff of file %s" % path)
            continue
        with Fold():
            print("verifying diff of file '%s'" % path)
            is_eol_distro = path in get_eol_distribution_filenames(url)
            data = load_yaml_with_lines(path)

            repos = data['repositories']
            if not repos:
                continue

            changed_repos = isolate_yaml_snippets_from_line_numbers(repos, lines)

            # print("In file: %s Changed repos are:" % path)
            # pprint.pprint(changed_repos)

            for n, r in changed_repos.items():
                errors = check_repo_for_errors(r)
                detected_errors.extend(["In file '''%s''': " % path + e
                                        for e in errors])
                if is_eol_distro:
                    errors = detect_post_eol_release(n, r, lines)
                    detected_errors.extend(["In file '''%s''': " % path + e
                                            for e in errors])

    for e in detected_errors:

        print("ERROR: %s" % e, file=sys.stderr)
    return detected_errors


class TestUrlValidity(unittest.TestCase):

    def test_function(self):
        detected_errors = main()
        self.assertFalse(detected_errors)

if __name__ == "__main__":
    detected_errors = main()
    if not detected_errors:
        sys.exit(0)
    sys.exit(1)
