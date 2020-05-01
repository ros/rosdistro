Migration Tools
===============

Utility scripts for migrating packages between rosdistros.

## Environment and setup

It's recommended to run this script within a virtualenv.
Python 3.6 or newer is required.

In addition to python3 you will also need Git installed.
If you are not already using a credential helper for https git remotes you will need to set one up:
https://git-scm.com/docs/gitcredentials

Install the script's dependencies listed in requirements.txt:

    python3 -m pip install -r requirements.txt

Make sure rosdep is initialized if it isn't already.

    sudo rosdep init

Configure a GitHub access token and release repository organization.
The token only needs public repository access and must belong to a member of the target GitHub organization with repository creation permissions.

```
GITHUB_TOKEN={token with public repository access}
export GITHUB_TOKEN
```

## Script arguments

The migration script has several named arguments, all of which are required.
* `--dest DEST_ROSDISTRO`: The rosdistro which will receive the newly bloomed repositories.
* `--source SOURCE_ROSDISTRO`: The rosdistro to take release repositories from for migration.
* `--source-ref GIT_COMMIT_ID_OR_REF`: The migration may be attempted multiple times. Each attempt must specify ref or commit to start from so that future changes to the source distribution do not unintentionally affect migration. This also enables platform migration without changing the rosdistro name.
* `--release-org GITHUB_ORG`: A GitHub organization for storing release repositories. If the repository does not exist in this organization a new repository will be created.

## Features

The migration tool currently performs the same operation for all intended use-cases and the different actions are accomplished by setting up the script with a different initial environment.

### Creating a new rosdistro from an existing one

This functionality is intended to support creating new stable ROS distributions from a perennial rolling distribution.

#### Prerequisites

* The local rosdistro index must already have an entry for the target distribution.
* The distribution.yaml file for the target must exist and should have an empty `repositories` field.


### Updating a migrated rosdistro 

This functionality is intended to support re-trying failed bloom releases in a ROS distribution migrated previously.

#### Prerequisites

* The local rosdistro index must already have an entry for the target distribution.
* The distribution.yaml must exist and may have some repositories already but repositories which failed to release must have no release version. Removing the release version for failed releases is the default behavior of this tool.


### Updating the platform of an existing rosdistro

This functionality is intended to support updating the supported platforms of the perennial rolling distribution.

#### Prerequisites

* A git commit id or ref name which has the previous platform and desired repositories in the source distribution.
* The current distribution.yaml should specify the desired target platforms and should have an empty `repositories` field.

