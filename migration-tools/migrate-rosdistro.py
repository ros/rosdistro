import argparse
import copy
import os
import os.path
import shutil
import subprocess
import sys
import tempfile

from bloom.commands.git.patch.common import get_patch_config, set_patch_config
from bloom.git import inbranch, show

import github
import yaml

from rosdistro import DistributionFile, get_distribution_cache, get_distribution_file, get_index
from rosdistro.writer import yaml_from_distribution_file

# These functions are adapted from Bloom's internal 'get_tracks_dict_raw' and
# 'write_tracks_dict_raw' functions.  We cannot use them directly since they
# make assumptions about the release repository that are not true during the
# manipulation of the release repository for this script.
def read_tracks_file():
    tracks_yaml = show('master', 'tracks.yaml')
    if tracks_yaml:
        return yaml.safe_load(tracks_yaml)
    else:
        raise ValueError('repository is missing tracks.yaml in master branch.')

@inbranch('master')
def write_tracks_file(tracks, commit_msg=None):
    if commit_msg is None:
        commit_msg = f'Update tracks.yaml from {sys.argv[0]}.'
    with open('tracks.yaml', 'w') as f:
        f.write(yaml.safe_dump(tracks, indent=2, default_flow_style=False))
    with open('.git/rosdistromigratecommitmsg', 'w') as f:
        f.write(commit_msg)
    subprocess.check_call(['git', 'add', 'tracks.yaml'])
    subprocess.check_call(['git', 'commit', '-F', '.git/rosdistromigratecommitmsg'])


parser = argparse.ArgumentParser(
    description='Import packages from one rosdistro into another one.'
)
parser.add_argument('--source', required=True, help='The source rosdistro name')
parser.add_argument('--source-ref', required=True, help='The git version for the source. Used to retry failed imports without bumping versions.')
parser.add_argument('--dest', required=True, help='The destination rosdistro name')
parser.add_argument('--release-org', required=True, help='The organization containing release repositories')

args = parser.parse_args()

gclient = github.Github(os.environ['GITHUB_TOKEN'])
release_org = gclient.get_organization(args.release_org)
org_release_repos = [r.name for r in release_org.get_repos() if r.name]

if not os.path.isfile('index-v4.yaml'):
    raise RuntimeError('This script must be run from a rosdistro index directory.')
rosdistro_dir = os.path.abspath(os.getcwd())
rosdistro_index_url = f'file://{rosdistro_dir}/index-v4.yaml'

index = get_index(rosdistro_index_url)
index_yaml = yaml.safe_load(open('index-v4.yaml', 'r'))

if len(index_yaml['distributions'][args.source]['distribution']) != 1 or \
        len(index_yaml['distributions'][args.dest]['distribution']) != 1:
            raise RuntimeError('Both source and destination distributions must have a single distribution file.')

# There is a possibility that the source_ref has a different distribution file
# layout. Check that they match.
source_ref_index_yaml = yaml.safe_load(show(args.source_ref, 'index-v4.yaml'))
if source_ref_index_yaml['distributions'][args.source]['distribution'] != \
  index_yaml['distributions'][args.source]['distribution']:
      raise RuntimeError('The distribution file layout has changed between the source ref and now.')

source_distribution_filename = index_yaml['distributions'][args.source]['distribution'][0]
dest_distribution_filename = index_yaml['distributions'][args.dest]['distribution'][0]

# Fetch the source distribution file from the exact point in the repository history requested.
source_distfile_data = yaml.safe_load(show(args.source_ref, source_distribution_filename))
source_distribution = DistributionFile(args.source, source_distfile_data)

# Prepare the destination distribution for new bloom releases from the source distribution.
dest_distribution = get_distribution_file(index, args.dest)
new_repositories = []
repositories_to_retry = []
for repo_name, repo_data in sorted(source_distribution.repositories.items()):
    if repo_name not in dest_distribution.repositories:
        dest_repo_data = copy.deepcopy(repo_data)
        if dest_repo_data.release_repository:
            new_repositories.append(repo_name)
            release_tag = dest_repo_data.release_repository.tags['release']
            release_tag = release_tag.replace(args.source,args.dest)
            dest_repo_data.release_repository.tags['release'] = release_tag
        dest_distribution.repositories[repo_name] = dest_repo_data
    elif dest_distribution.repositories[repo_name].release_repository is not None and \
            dest_distribution.repositories[repo_name].release_repository.version is None:
        dest_distribution.repositories[repo_name].release_repository.version = repo_data.release_repository.version
        repositories_to_retry.append(repo_name)
    else:
        # Nothing to do if the release is there.
        pass

print(f'Found {len(new_repositories)} new repositories to release:', new_repositories)
print(f'Found {len(repositories_to_retry)} repositories to retry:', repositories_to_retry)

# Copy out an optimistic destination distribution file to bloom everything
# against. This obviates the need to bloom packages in a topological order or
# do any special handling for dependency cycles between repositories as are
# known to occur in the ros2/launch repository.  To allow this we must keep
# track of repositories that fail to bloom and pull their release in a cleanup
# step.
with open(dest_distribution_filename, 'w') as f:
    f.write(yaml_from_distribution_file(dest_distribution))

repositories_bloomed = []
repositories_with_errors = []

workdir = tempfile.mkdtemp()
os.chdir(workdir)
os.environ['ROSDISTRO_INDEX_URL'] = rosdistro_index_url
os.environ['BLOOM_SKIP_ROSDEP_UPDATE'] = '1'

# This call to update rosdep is critical because we're setting
# ROSDISTRO_INDEX_URL above and also suppressing the automatic
# update in Bloom itself.
subprocess.check_call(['rosdep', 'update'])

for repo_name in sorted(new_repositories + repositories_to_retry):
    try:
        release_spec = dest_distribution.repositories[repo_name].release_repository
        print('Adding repo:', repo_name)
        if release_spec.type != 'git':
            raise ValueError('This script can only handle git repositories.')
        if release_spec.version is None:
            raise ValueError(f'{repo_name} is not released in the source distribution (release version is missing or blank).')
        remote_url = release_spec.url
        release_repo = remote_url.split('/')[-1]
        if release_repo.endswith('.git'):
            release_repo = release_repo[:-4]
        subprocess.check_call(['git', 'clone', remote_url])
        os.chdir(release_repo)
        tracks = read_tracks_file()

        if not tracks['tracks'].get(args.source):
            raise ValueError('Repository has not been released.')

        if release_repo not in org_release_repos:
            release_org.create_repo(release_repo)
        new_release_repo_url = f'https://github.com/{args.release_org}/{release_repo}.git'
        subprocess.check_call(['git', 'remote', 'rename', 'origin', 'oldorigin'])
        subprocess.check_call(['git', 'remote', 'set-url', '--push', 'oldorigin', 'no_push'])
        subprocess.check_call(['git', 'remote', 'add', 'origin', new_release_repo_url])

        if args.source != args.dest:
            # Copy a bloom .ignored file from source to target distro.
            if os.path.isfile(f'{args.source}.ignored'):
                shutil.copyfile(f'{args.source}.ignored', f'{args.dest}.ignored')
                with open('.git/rosdistromigratecommitmsg', 'w') as f:
                    f.write(f'Propagate {args.source} ignore file to {args.dest}.')
                subprocess.check_call(['git', 'add', f'{args.dest}.ignored'])
                subprocess.check_call(['git', 'commit', '-F', '.git/rosdistromigratecommitmsg'])

            # Copy the source track to the new destination.
            dest_track = copy.deepcopy(tracks['tracks'][args.source])
            dest_track['ros_distro'] = args.dest
            tracks['tracks'][args.dest] = dest_track
            ls_remote = subprocess.check_output(['git', 'ls-remote', '--heads', 'oldorigin', f'*{args.source}*'], universal_newlines=True)
            for line in ls_remote.split('\n'):
                if line == '':
                    continue
                obj, ref = line.split('\t')
                ref = ref[11:] # strip 'refs/heads/'
                newref = ref.replace(args.source, args.dest)
                subprocess.check_call(['git', 'branch', newref, obj])
                if newref.startswith('patches/'):
                    # Update parent in patch configs. Without this update the
                    # patches will be rebased out when git-bloom-release is
                    # called because the configured parent won't match the
                    # expected source branch.
                    config = get_patch_config(newref)
                    config['parent'] = config['parent'].replace(args.source, args.dest)
                    set_patch_config(newref, config)
            # Check for a release repo url in the track configuration
            if 'release_repo_url' in dest_track:
                dest_track['release_repo_url'] = None
            write_tracks_file(tracks, f'Copy {args.source} track to {args.dest} with migrate-rosdistro.py.')
        else:
            dest_track = tracks['tracks'][args.dest]

        # Configure next release to re-release previous version into the
        # destination.  A version value of :{ask} will fail due to
        # interactivity and :{auto} may result in a previously unreleased tag
        # on the development branch being released for the first time.
        if dest_track['version'] in [':{ask}', ':{auto}']:
            # Override the version for this release to guarantee the same version from our
            # source distribution is released.
            dest_track['version_saved'] = dest_track['version']
            source_version, source_inc = source_distribution.repositories[repo_name].release_repository.version.split('-')
            dest_track['version'] = source_version
            write_tracks_file(tracks, f'Update {args.dest} track to release the same version as the source distribution.')

        if dest_track['release_tag'] == ':{ask}' and 'last_release' in dest_track:
            # Override the version for this release to guarantee the same version is released.
            dest_track['release_tag_saved'] = dest_track['release_tag']
            dest_track['release_tag'] = dest_track['last_release']
            write_tracks_file(tracks, f'Update {args.dest} track to release exactly last-released tag.')

        # Update release increment for the upcoming release.
        # We increment whichever is greater between the source distribution's
        # release increment and the release increment in the bloom track since
        # there may be releases that were not committed to the source
        # distribution.
        # This heuristic does not fully cover situations where the version in
        # the source distribution and the version in the release track differ.
        # In that case it is still possible for this tool to overwrite a
        # release increment if the greatest increment of the source version is
        # not in the source distribution and does not match the version
        # currently in the release track.
        release_inc = str(max(int(source_inc), int(dest_track['release_inc'])) + 1)

        # Bloom will not run with multiple remotes.
        subprocess.check_call(['git', 'remote', 'remove', 'oldorigin'])
        subprocess.check_call(['git', 'bloom-release', '--non-interactive', '--release-increment', release_inc, '--unsafe', args.dest], stdin=subprocess.DEVNULL, env=os.environ)
        subprocess.check_call(['git', 'push', 'origin', '--all', '--force'])
        subprocess.check_call(['git', 'push', 'origin', '--tags', '--force'])
        subprocess.check_call(['git', 'checkout', 'master'])

        # Re-read tracks.yaml after release.
        tracks = read_tracks_file()
        dest_track = tracks['tracks'][args.dest]
        if 'version_saved' in dest_track:
            dest_track['version'] = dest_track['version_saved']
            del dest_track['version_saved']
            write_tracks_file(tracks, f'Restore saved version for {args.dest} track.')
        if 'release_tag_saved' in dest_track:
            dest_track['release_tag'] = dest_track['release_tag_saved']
            del dest_track['release_tag_saved']
            write_tracks_file(tracks, f'Restore saved version and tag for {args.dest} track.')
        new_release_track_inc = str(int(tracks['tracks'][args.dest]['release_inc']))
        release_spec.url = new_release_repo_url

        ver, _inc = release_spec.version.split('-')
        release_spec.version = '-'.join([ver, new_release_track_inc])
        repositories_bloomed.append(repo_name)
        subprocess.check_call(['git', 'push', 'origin', 'master'])
    except (subprocess.CalledProcessError, ValueError, github.GithubException) as e:
        repositories_with_errors.append((repo_name, e))
    os.chdir(workdir)

os.chdir(rosdistro_dir)

for dest_repo in sorted(new_repositories + repositories_to_retry):
    if dest_repo not in repositories_bloomed:
        print(f'{dest_repo} was not bloomed! Removing the release version,')
        dest_distribution.repositories[dest_repo].release_repository.version = None

with open(dest_distribution_filename, 'w') as f:
    f.write(yaml_from_distribution_file(dest_distribution))

print(f'Had {len(repositories_with_errors)} repositories with errors:', repositories_with_errors)
