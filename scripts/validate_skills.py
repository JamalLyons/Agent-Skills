#!/usr/bin/env python3
"""Validate portable skill metadata and resources; optional host UI metadata stays optional."""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

try:
    import yaml
except ImportError:
    raise SystemExit('Skill metadata checks need PyYAML. Install development dependencies with '
                     'python3 -m pip install -r requirements-dev.txt (prefer a virtual environment).') from None

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class MetadataError(ValueError):
    pass


class UniqueSafeLoader(yaml.SafeLoader):
    """Duplicate keys make skill identity ambiguous, so do not silently keep the last one."""


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            if key in result:
                raise MetadataError(f'duplicate YAML key: {key!r}')
            result[key] = loader.construct_object(value_node, deep=deep)
        except TypeError:
            raise MetadataError('YAML mapping keys must be scalar values') from None
    return result


UniqueSafeLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse_yaml(text, source):
    try:
        data = yaml.load(text, Loader=UniqueSafeLoader)
    except (yaml.YAMLError, MetadataError) as exc:
        raise MetadataError(f'{source}: invalid YAML: {exc}') from exc
    if not isinstance(data, dict) or not all(isinstance(key, str) for key in data):
        raise MetadataError(f'{source}: YAML must be a mapping with string keys')
    return data


def frontmatter(path):
    lines = path.read_text(encoding='utf-8-sig').splitlines()
    if not lines or lines[0] != '---':
        raise MetadataError(f'{path}: start the file with YAML frontmatter delimited by ---')
    try:
        end = lines.index('---', 1)
    except ValueError:
        raise MetadataError(f'{path}: missing closing frontmatter delimiter') from None
    return parse_yaml('\n'.join(lines[1:end]), path)


def bounded_string(data, key, source, maximum=None, required=False):
    if key not in data and not required:
        return
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or (maximum and len(value) > maximum):
        limit = f' of at most {maximum} characters' if maximum else ''
        raise MetadataError(f'{source}: {key} must be a nonempty string{limit}')


def validate_ui(path):
    """Check supplied host hints without making them part of the portable skill contract."""
    data = parse_yaml(path.read_text(encoding='utf-8'), path)
    for section in ('interface', 'policy', 'dependencies'):
        if section in data and not isinstance(data[section], dict):
            raise MetadataError(f'{path}: {section} must be a mapping')
    interface = data.get('interface', {})
    for key, value in interface.items():
        if not isinstance(key, str) or not isinstance(value, str) or not value.strip():
            raise MetadataError(f'{path}: interface values must be nonempty strings')
    policy = data.get('policy', {})
    if 'allow_implicit_invocation' in policy and type(policy['allow_implicit_invocation']) is not bool:
        raise MetadataError(f'{path}: policy.allow_implicit_invocation must be a boolean')
    for key in ('icon_small', 'icon_large'):
        if key in interface and not (path.parent.parent / interface[key]).is_file():
            raise MetadataError(f'{path}: missing {key} resource {interface[key]}')


def validate_resources(skill):
    for doc in skill.rglob('*.md'):
        prose = re.sub(r'(?ms)^```.*?^```[^\n]*', '', doc.read_text(encoding='utf-8'))
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', prose):
            target = target.strip().strip('<>')
            if not target or target.startswith('#') or urlsplit(target).scheme:
                continue
            local = unquote(target.split('#', 1)[0])
            if not (doc.parent / local).exists():
                raise MetadataError(f'{doc}: missing local resource {target}')


def validate_skill(skill):
    skill = Path(skill)
    entrypoint = skill / 'SKILL.md'
    data = frontmatter(entrypoint)
    bounded_string(data, 'name', entrypoint, 64, required=True)
    if not NAME.fullmatch(data['name']) or data['name'] != skill.name:
        raise MetadataError(f'{entrypoint}: name must match its directory and use lowercase letters, digits, and single hyphens')
    bounded_string(data, 'description', entrypoint, 1024, required=True)
    bounded_string(data, 'compatibility', entrypoint, 500)
    bounded_string(data, 'license', entrypoint)
    bounded_string(data, 'allowed-tools', entrypoint)
    if 'metadata' in data and (not isinstance(data['metadata'], dict) or
                              not all(isinstance(k, str) and isinstance(v, str) for k, v in data['metadata'].items())):
        raise MetadataError(f'{entrypoint}: metadata must map strings to strings')
    validate_resources(skill)
    ui = skill / 'agents/openai.yaml'
    if ui.exists():
        validate_ui(ui)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('skills', nargs='*', type=Path, help='skill directories; default: all repository skills')
    args = parser.parse_args(argv)
    paths = args.skills or sorted(path.parent for path in (ROOT / 'skills').glob('*/SKILL.md'))
    errors = []
    for skill in paths:
        try:
            validate_skill(skill)
        except (MetadataError, OSError, UnicodeError) as exc:
            errors.append(str(exc))
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        return 1
    print(f'Validated {len(paths)} portable skill packages; host UI metadata is optional.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
