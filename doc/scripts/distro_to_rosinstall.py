#! /usr/bin/env python

import os
import sys
import yaml
from rospkg.distro import load_distro, distro_uri

def translate(distro, translate_dir):
    d = load_distro(distro_uri(distro))
    repo_list = d.get_stacks(True)
    for name, item in repo_list.iteritems():
        if item.vcs_config.type == 'svn':
            rosinstall = [{item.vcs_config.type: \
                           {'local-name': item.name,
                            'uri': item.vcs_config.anon_dev}}]
        else:
            rosinstall = [{item.vcs_config.type: \
                           {'local-name': item.name,
                            'uri': item.vcs_config.anon_repo_uri,
                            'version': item.vcs_config.dev_branch}}]

        path = os.path.join(translate_dir, "%s.rosinstall" % item.name)
        with open(path, 'w+') as f:
            print("writing to %s" % path)
            yaml.safe_dump(rosinstall, f, default_flow_style=False)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Use %s distro install_folder" % sys.argv[0])
        sys.exit()
    translate(sys.argv[1], sys.argv[2])
