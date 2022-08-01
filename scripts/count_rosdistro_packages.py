#!/usr/bin/env python3

# Copyright (c) 2017, Open Source Robotics Foundation
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
valid_distros = ['groovy', 'hydro', 'indigo', 'jade', 'kinetic', 'lunar', 'melodic', 'noetic',
    'ardent', 'bouncy', 'crystal', 'dashing', 'eloquent', 'foxy', 'galactic', 'rolling']

FIRST_HASH = 'be9218681f14d0fac908da46902eb2f1dad084fa'
OUTPUT_FILE = args.output_file


def get_all_commits(repo_dir, first_hash):
    return subprocess.check_output('git -C %s rev-list --reverse %s..master' % (repo_dir, first_hash), shell=True).decode("utf-8").splitlines()


def get_commit_date(repo_dir, commit):
    date_str = subprocess.check_output('git -C %s show -s --format=%%ci %s' % (repo_dir, commit), shell=True).decode("utf-8").strip()
    return date_str


def get_rosdistro_counts(index_path):
    index_uri = os.path.join(index_path, 'index.yaml')
    if not os.path.exists(index_uri):
        print('failed to find %s falling back to v4' % index_uri)
        index_uri = os.path.join(index_path, 'index-v4.yaml')
        if not os.path.exists(index_uri):
            print('Could not find index at this path either %s %s' % (index_path, index_uri))
            subprocess.call('ls %s' % index_path, shell=True)
            return []
    index_uri = 'file://' + index_uri
    i = rosdistro.get_index(index_uri)
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
        counts = get_rosdistro_counts(repo_location)
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
    outfh.write(', '.join(['date'] + valid_distros))
    for l in csv_strings:
        outfh.write(l + '\n')
