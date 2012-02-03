#!/usr/bin/env python
import yaml, argparse

parser = argparse.ArgumentParser(description='Sort the release yaml db in place.')
parser.add_argument('yaml_file',help='the yaml file to update')
args = parser.parse_args()
db = yaml.load(open(args.yaml_file,'r'))
db = sorted(db)
new_db = []
for x in db:
    new_db.append("- url: %s"%x['url'])
    new_db.append("  target: %s"%x['target'])
with open(args.yaml_file, 'w') as f:
    f.write('\n'.join(new_db) + '\n')
