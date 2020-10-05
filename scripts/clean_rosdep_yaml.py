#!/usr/bin/env python

import yaml
import argparse
import re
import io

dont_bracket = ['uri', 'md5sum']


def paddify(s, l):
    a = s.split('\n')
    buf = ''
    pad = '  ' * l
    for i, r in enumerate(a[:-1]):
        buf += "%s%s\n" % (pad, r)
    return buf


def quote_if_necessary(s):
    if type(s) is list:
        return [quote_if_necessary(a) for a in s]
    return re.search('a: (.*)\n', yaml.dump({'a': s})).group(1)


def prn(n, nm, lvl):
    if nm == '*':
        # quote wildcard keys
        nm = "'*'"
    else:
        # quote numeric keys
        try:
            nm_int = int(nm)
        except ValueError:
            pass
        else:
            if str(nm_int) == nm:
                nm = "'%d'" % nm_int
    pad = '  ' * lvl
    if isinstance(n, list):
        return "%s%s: [%s]\n" % (pad, nm, ', '.join(quote_if_necessary(n)))
    elif n is None:
        return "%s%s: %s\n" % (pad, nm, 'null')
    elif isinstance(n, str):
        if len(n.split('\n')) > 1:
            return "%s%s: |\n%s" % (pad, nm, paddify(n, lvl+1))
        else:
            if nm in dont_bracket:
                return "%s%s: %s\n" % (pad, nm, quote_if_necessary(n))
            return "%s%s: [%s]\n" % (pad, nm, ', '.join(quote_if_necessary(n.split())))
    buf = "%s%s:\n" % (pad, nm)
    for a in sorted(n.keys()):
        buf += prn(n[a], a, lvl+1)
    return buf


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Cleans a rosdep YAML file to a correct format')
    parser.add_argument('infile', help='input rosdep YAML file')
    parser.add_argument('outfile', help='output YAML file to be written')
    args = parser.parse_args()

    with open(args.infile) as f:
        iny = yaml.safe_load(f.read())

    buf = ''
    for a in sorted(iny):
        buf += prn(iny[a], a, 0)

    with io.open(args.outfile, 'wb') as f:
        f.write(buf.encode('utf-8'))
