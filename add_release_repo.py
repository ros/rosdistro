#!/usr/bin/env python
import yaml, argparse

parser = argparse.ArgumentParser(description='Insert an git buildpackage repo into the yaml database.')
parser.add_argument('yaml_file',help='the yaml file to update')
parser.add_argument('clone_url',help='a clonable url')
parser.add_argument('--target',help='the target ubuntu distros. default : %(default)s', default='all')
args = parser.parse_args()
db = yaml.load(open(args.yaml_file,'r'))
db.append(dict(url=args.clone_url,target=args.target))
db = sorted(db)
new_db = []
for x in db:
    new_db.append("- url: %s"%x['url'])
    new_db.append("  target: %s"%x['target'])
with open(args.yaml_file, 'w') as f:
    f.write('\n'.join(new_db) + '\n')
