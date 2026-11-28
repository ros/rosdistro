import pytest
import yaml

from .verify import verify_rules
from .yaml import AnnotatedSafeLoader
from .yaml import isolate_yaml_snippets_from_line_numbers


@pytest.mark.parametrize(('source', 'line', 'expected'), [
    (
        'example:\n  ubuntu:\n    jammy: [example-old]\n    noble: null\n',
        4,
        {'example': {'ubuntu': {'noble': None}}},
    ),
    (
        'example:\n  debian: [example]\n  ubuntu: null\n',
        3,
        {'example': {'ubuntu': None}},
    ),
    (
        "example:\n  ubuntu:\n    '*': null\n    jammy: [example-old]\n",
        3,
        {'example': {'ubuntu': {'*': None}}},
    ),
])
def test_isolate_null_rule(source, line, expected):
    rules = yaml.load(source, Loader=AnnotatedSafeLoader)

    assert isolate_yaml_snippets_from_line_numbers(rules, [line]) == expected


def test_isolate_changed_package_and_null_rule():
    rules = yaml.load(
        'example:\n'
        '  ubuntu:\n'
        '    jammy: [example-old]\n'
        '    noble: null\n'
        '    resolute: [example-new]\n',
        Loader=AnnotatedSafeLoader,
    )

    assert isolate_yaml_snippets_from_line_numbers(rules, [4, 5]) == {
        'example': {'ubuntu': {'noble': None, 'resolute': ['example-new']}},
    }


@pytest.mark.parametrize(('lines', 'expected'), [
    ([3], {'ubuntu': {'jammy': ['example-old']}}),
    ([5], {'ubuntu': {'resolute': ['example-new', 'example-extra']}}),
    ([6, 7], {'ubuntu': {'resolute': ['example-new', 'example-extra']}}),
    ([8], {'debian': ['example-debian', 'example-common']}),
    ([9, 10], {'debian': ['example-debian', 'example-common']}),
])
def test_isolate_packages_around_null_rule(lines, expected):
    rules = yaml.load(
        'example:\n'
        '  ubuntu:\n'
        '    jammy: [example-old]\n'
        '    noble: null\n'
        '    resolute:\n'
        '      - example-new\n'
        '      - example-extra\n'
        '  debian: [\n'
        '    example-debian,\n'
        '    example-common]\n',
        Loader=AnnotatedSafeLoader,
    )

    assert isolate_yaml_snippets_from_line_numbers(rules, lines) == {
        'example': expected,
    }


def test_null_only_change_does_not_check_unmodified_packages(monkeypatch):
    rules = yaml.load(
        'example:\n'
        '  ubuntu:\n'
        '    jammy: [example-old]\n'
        '    noble: null\n',
        Loader=AnnotatedSafeLoader,
    )
    changed_rules = isolate_yaml_snippets_from_line_numbers(rules, [4])
    config = {
        'package_sources': {'ubuntu': []},
        'supported_versions': {'ubuntu': ['jammy', 'noble']},
        'supported_arches': {'ubuntu': ['amd64']},
        'name_replacements': {},
    }

    def unexpected_package_check(*args):
        pytest.fail('A null-only change must not check an unmodified package')

    monkeypatch.setattr(
        'test.rosdep_repo_check.verify.find_package', unexpected_package_check)

    assert list(verify_rules(config, changed_rules, rules)) == []
