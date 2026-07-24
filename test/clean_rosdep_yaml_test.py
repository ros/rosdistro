#!/usr/bin/env python

import yaml

from scripts.clean_rosdep_yaml import prn, quote_if_necessary


def render(data):
    # Render a rosdep dict exactly the way clean_rosdep_yaml.py's __main__ does.
    return ''.join(prn(data[key], key, 0) for key in sorted(data))


def test_quote_if_necessary_quotes_flow_indicators():
    # Values containing YAML flow indicators ('{', '}', '[', ']', ...) must be
    # quoted so they stay valid once emitted inside a flow sequence ('[...]').
    for value in [
        '${PYTHON_PN}-numpy@openembedded-core',
        'python%{python3_pkgversion}-devel',
        'dev-libs/boost[python]',
        'glibc-devel(%{__isa_name}-32)',
    ]:
        quoted = quote_if_necessary(value)
        assert yaml.safe_load('[%s]' % quoted) == [value]


def test_quote_if_necessary_leaves_plain_values_unquoted():
    # Ordinary package names must not gain spurious quotes.
    for value in ['python3-numpy', 'py27-numpy', 'Adafruit-ADS1x15']:
        assert quote_if_necessary(value) == value


def test_float_like_version_keys_are_quoted():
    # A key such as '15.2' must be quoted, otherwise it is re-read as a float
    # and check_rosdep.py's string comparisons fail.
    data = {'some-dep': {'opensuse': {'15.2': ['foo']}}}
    rendered = render(data)
    assert "'15.2':" in rendered
    assert yaml.safe_load(rendered) == data


def test_integer_version_keys_are_quoted():
    # Regression guard for the pre-existing integer-key behaviour.
    data = {'some-dep': {'rhel': {'8': ['bar']}}}
    rendered = render(data)
    assert "'8':" in rendered
    assert yaml.safe_load(rendered) == data


def test_roundtrip_preserves_special_characters():
    # End-to-end: an entry exercising both bugs must render to valid YAML that
    # loads back to exactly the same structure.
    data = {
        'some-dep': {
            'fedora': ['glibc-devel(%{__isa_name}-32)', 'glibc-static'],
            'gentoo': ['dev-libs/boost[python]'],
            'openembedded': ['${PYTHON_PN}-numpy@openembedded-core'],
            'opensuse': {'15.2': ['foo'], '15.3': ['bar']},
            'rhel': {'8': ['baz']},
            'ubuntu': ['python3-numpy'],
        },
    }
    assert yaml.safe_load(render(data)) == data
