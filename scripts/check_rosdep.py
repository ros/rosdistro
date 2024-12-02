#!/usr/bin/env python

from __future__ import print_function

import re
import yaml
import argparse
import sys

indent_atom = '  '

# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#
# With modifications
#           (C) 2013 Paul M <pmathieu@willowgarage.com>

codeCodes = {
    'black':     '0;30',     'bright gray':   '0;37',
    'blue':      '0;34',     'white':         '1;37',
    'green':     '0;32',     'bright blue':   '1;34',
    'cyan':      '0;36',     'bright green':  '1;32',
    'red':       '0;31',     'bright cyan':   '1;36',
    'purple':    '0;35',     'bright red':    '1;31',
    'yellow':    '0;33',     'bright purple': '1;35',
    'dark gray': '1;30',     'bright yellow': '1;33',
    'normal':    '0'
}


def printc(text, color):
    """Print in color."""
    if sys.stdout.isatty():
        print("\033["+codeCodes[color]+"m"+text+"\033[0m")
    else:
        print(text)


def print_test(msg):
    printc(msg, 'yellow')


def print_err(msg):
    printc('  ERR: ' + msg, 'red')


def no_trailing_spaces(buf):
    clean = True
    for i, l in enumerate(buf.split('\n')):
        if re.search(r' $', l) is not None:
            print_err("trailing space line %u" % (i+1))
            clean = False
    return clean


def no_blank_lines(buf):
    clean = True
    for i, l in enumerate(buf.split('\n')[:-1]):
        if re.match(r'^\s*$', l):
            print_err("blank line %u" % (i+1))
            clean = False
    return clean


def generic_parser(buf, cb):
    ilen = len(indent_atom)
    stringblock = False
    strlvl = 0
    lvl = 0
    clean = True

    for i, l in enumerate(buf.split('\n')):
        if l == '':
            continue
        if re.search(r'^\s*#', l) is not None:
            continue
        try:
            s = re.search(r'(?!' + indent_atom + r')[^\s]', l).start()
        except:
            print_err("line %u: %s" % (i, l))
            raise
        if stringblock:
            if int(s / ilen) > strlvl:
                continue
            stringblock = False
        lvl = int(s / ilen)
        opts = {'lvl': lvl, 's': s}
        if not cb(i, l, opts):
            clean = False
        if re.search(r'\|$|\?$|^\s*\?', l) is not None:
            stringblock = True
            strlvl = lvl
    return clean


def correct_indent(buf):
    ilen = len(indent_atom)

    def fun(i, l, o):
        s = o['s']
        olvl = fun.lvl
        lvl = o['lvl']
        fun.lvl = lvl
        if s % ilen > 0:
            print_err("invalid indentation level line %u: %u" % (i+1, s))
            return False
        if lvl > olvl + 1:
            print_err("too much indentation line %u" % (i+1))
            return False
        return True
    fun.lvl = 0
    return generic_parser(buf, fun)


def check_brackets(buf):
    excepts = ['uri', 'md5sum']

    def fun(i, l, o):
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):\s*(\w.*)$', l)
        if m is not None and m.groups()[0] not in excepts:
            if m.groups()[1] == 'null':
                return True
            print_err("list not in square brackets line %u" % (i+1))
            return False
        return True
    return generic_parser(buf, fun)


def check_order(buf):
    def fun(i, l, o):
        lvl = o['lvl']
        st = fun.namestack
        while len(st) > lvl + 1:
            st.pop()
        if len(st) < lvl + 1:
            st.append('')
        if re.search(r'^\s*\?', l) is not None:
            return True
        m = re.match(r'^(?:' + indent_atom + r')*([^:]*):.*$', l)
        prev = st[lvl]
        try:
            # parse as yaml to parse `"foo bar"` as string 'foo bar' not string '"foo bar"'
            item = yaml.safe_load(m.groups()[0])
        except:
            print('woops line %d' % i)
            raise
        st[lvl] = item
        if item < prev:
            print_err("list out of alphabetical order line %u.  '%s' should come before '%s'" % ((i+1), item, prev))
            return False
        return True
    fun.namestack = ['']
    return generic_parser(buf, fun)


def main(fname):
    with open(fname) as f:
        buf = f.read()

    def my_assert(val):
        if not val:
            my_assert.clean = False
    my_assert.clean = True

    # here be tests.
    ydict = None
    try:
        ydict = yaml.safe_load(buf)
    except Exception:
        pass
    if ydict != {}:
        print_test("checking for trailing spaces...")
        my_assert(no_trailing_spaces(buf))
        print_test("checking for blank lines...")
        my_assert(no_blank_lines(buf))
        print_test("checking for incorrect indentation...")
        my_assert(correct_indent(buf))
        print_test("checking for non-bracket package lists...")
        my_assert(check_brackets(buf))
        print_test("checking for item order...")
        my_assert(check_order(buf))
        print_test("building yaml dict...")
    else:
        print_test("skipping file with empty dict contents...")
    try:
        ydict = yaml.safe_load(buf)

        # ensure that values don't contain whitespaces
        whitespace_whitelist = ["el capitan", "mountain lion"]

        def walk(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    walk(key)
                    walk(value)
            if isinstance(node, list):
                for value in node:
                    walk(value)
            if isinstance(node, str) and re.search(r'\s', node) and node not in whitespace_whitelist:
                    print_err("value '%s' must not contain whitespaces" % node)
                    my_assert(False)
        walk(ydict)

    except Exception as e:
        print_err("could not build the dict: %s" % (str(e)))
        my_assert(False)

    if not my_assert.clean:
        printc("there were errors, please correct the file", 'bright red')
        return False
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checks whether yaml syntax corresponds to ROS rules')
    parser.add_argument('infile', help='input rosdep YAML file')
    args = parser.parse_args()

    if not main(args.infile):
        sys.exit(1)
