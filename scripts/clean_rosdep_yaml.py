#!/usr/bin/env python

import yaml
import argparse

dont_bracket = ['uri', 'md5sum']
use_quotes = ['>', '=']

def paddify(s, l):
    a = s.split('\n')
    buf = ''
    pad = '  ' * l
    for i, r in enumerate(a[:-1]):
        buf += "%s%s\n" % (pad, r)
    return buf

def prn(n, nm, lvl):
    pad = '  ' * lvl
    if isinstance(n, list):
        return "%s%s: [%s]\n" % (pad, nm, ', '.join(n))
    elif n is None:
        return "%s%s:\n" % (pad, nm)
    elif isinstance(n, str):
        if len(n.split('\n')) > 1:
            return "%s%s: |\n%s" % (pad, nm, paddify(n, lvl+1))
        else:
            if n.lstrip()[0] in use_quotes:
                return "%s%s: ['%s']\n" % (pad, nm, "', '".join(n.split()))
            if nm in dont_bracket:
                return "%s%s: %s\n" % (pad, nm, n)
            return "%s%s: [%s]\n" % (pad, nm, ', '.join(n.split()))
    buf = "%s%s:\n" % (pad, nm)
    for a in sorted(n.keys()):
        buf += prn(n[a], a, lvl+1)
    return buf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Cleans a rosdep YAML file to a correct format')
    parser.add_argument('infile', help='input rosdep YAML file')
    parser.add_argument('outfile', help='output YAML file to be written')
    args = parser.parse_args()

    with open(args.infile) as f:
        iny = yaml.load(f.read())

    buf = ''
    for a in sorted(iny):
        buf += prn(iny[a], a, 0)

    with open(args.outfile, 'w') as f:
        f.write(buf)
