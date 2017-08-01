#!/usr/bin/env python3

# Copyright 2017 Open Source Robotics Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
from dateutil import parser as dateparser
import os
import rosdistro
import shutil
import subprocess

import tempfile

parser = argparse.ArgumentParser(description='Count packages in the rosdistro')
parser.add_argument('--repo-location', metavar='Path to rosdistro', type=str,
                    help='The path to the rosdistro checkout')
parser.add_argument('--output-file', metavar='Path to output file', type=str,
                    help='The path to the output', default='output.csv')

args = parser.parse_args()

# if not os.path.exists(args.index_path):
#     parser.error("invalid rosdistro index url")
valid_distros = ['groovy', 'hydro', 'indigo', 'jade', 'kinetic', 'lunar']

FIRST_HASH = 'be9218681f14d0fac908da46902eb2f1dad084fa'
OUTPUT_FILE = args.output_file


def get_all_commits(repo_dir, first_hash):
    return subprocess.check_output('git -C %s rev-list --reverse %s..master' % (repo_dir, first_hash), shell=True).decode("utf-8").splitlines()


def get_commit_date(repo_dir, commit):
    date_str = subprocess.check_output('git -C %s show -s --format=%%ci %s' % (repo_dir, commit), shell=True).decode("utf-8").strip()
    return date_str


def get_rosdistro_counts(index_path):
    i = rosdistro.get_index(index_path)
    results = []
    for d in valid_distros:
        try:
            d_file = rosdistro.get_distribution_file(i, d)
            count = len(d_file.release_packages)
            results.append(count)
        except:
            results.append(0)
    return results


def monthly_commits(repo_dir, commits):
    '''A generator to downsample commits to be the first one per month.'''
    last_year = 0
    last_month = 0
    for commit in commits:
        dt = dateparser.parse(get_commit_date(repo_dir, commit))
        if dt.year > last_year:
            last_month = 0
            last_year = dt.year
        if dt.month > last_month:
            last_month = dt.month
            yield commit


if args.repo_location:
    repo_location = args.repo_location
else:
    repo_location = tempfile.mkdtemp()
    print("created repo_location %s" % repo_location)

try:
    if os.path.exists(os.path.join(repo_location, '.git')):
        subprocess.check_call('git -C %s fetch' % repo_location, shell=True)
    else:
        subprocess.check_call('git clone https://github.com/ros/rosdistro.git %s' % repo_location, shell=True)
        print("Cloned to %s" % repo_location)

    commits = get_all_commits(repo_location, FIRST_HASH)

    print("Commits: %s" % len(commits))

    csv_strings = []
    for commit in monthly_commits(repo_location, commits):
        subprocess.check_call('git -C %s clean -fxd' % repo_location, shell=True)
        subprocess.check_call('git -C %s checkout --quiet %s' % (repo_location, commit), shell=True)
        commit_date = get_commit_date(repo_location, commit)
        counts = get_rosdistro_counts('file://%s/index.yaml' % repo_location)
        csv_strings.append(", ".join([commit_date] + [str(c) for c in counts]))
        print("progress: %s" % csv_strings[-1])

# except Exception as ex:
#     print("Exception:: %s" % ex)
finally:
    if not args.repo_location:
        shutil.rmtree(repo_location)
        print("cleaned up repo_location %s" % repo_location)


with open(OUTPUT_FILE, 'w') as outfh:
    print("Writing to %s" % OUTPUT_FILE)
    for l in csv_strings:
        outfh.write(l + '\n')
