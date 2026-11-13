"""Exercise parsed YAML semantics and portable package constraints using disposable skills."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metadata_validator', ROOT / 'scripts/validate_skills.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.skill = Path(self.tmp.name) / 'example'
        self.skill.mkdir()

    def write(self, yaml_text='name: example\ndescription: Useful test skill.', body=''):
        (self.skill / 'SKILL.md').write_text(f'---\n{yaml_text}\n---\n{body}')

    def assert_invalid(self, yaml_text, pattern):
        self.write(yaml_text)
        with self.assertRaisesRegex(validator.MetadataError, pattern):
            validator.validate_skill(self.skill)

    def test_folded_description_and_optional_host_metadata(self):
        self.write('name: example\ndescription: >-\n  Investigate a problem\n  using primary sources.\nmetadata:\n  author: "A person"')
        data = validator.validate_skill(self.skill)
        self.assertEqual(data['description'], 'Investigate a problem using primary sources.')
        self.assertFalse((self.skill / 'agents/openai.yaml').exists())

    def test_required_values_are_parsed_not_matched_as_text(self):
        for text, pattern in [
            ('name: example\ndescription: [one, two]', 'description'),
            ('name: example\ndescription: true', 'description'),
            ('name: example\ndescription: "   "', 'description'),
            ('name: example\n# description: only a comment', 'description'),
            ('name: other\ndescription: Useful.', 'match its directory'),
            ('name: example\ndescription: First\ndescription: Second', 'duplicate YAML key'),
            ('name: example\ndescription: [broken', 'invalid YAML'),
        ]:
            with self.subTest(yaml=text):
                self.assert_invalid(text, pattern)

    def test_description_and_compatibility_boundaries(self):
        self.write('name: example\ndescription: "' + 'd' * 1024 + '"\ncompatibility: "' + 'c' * 500 + '"')
        validator.validate_skill(self.skill)
        self.assert_invalid('name: example\ndescription: "' + 'd' * 1025 + '"', '1024')
        self.assert_invalid('name: example\ndescription: Valid.\ncompatibility: "' + 'c' * 501 + '"', '500')

    def test_names_have_portable_shape_and_length(self):
        for name in ('Example', '-example', 'example-', 'two--hyphens', 'x' * 65):
            with self.subTest(name=name):
                self.assert_invalid(f'name: {name}\ndescription: Useful.', 'name')

    def test_metadata_and_known_optional_field_types(self):
        for extra in ('metadata: []', 'metadata:\n  count: 3', 'metadata:\n  4: value',
                      'compatibility: [bash]', 'license: true', 'allowed-tools: [Read]'):
            with self.subTest(extra=extra):
                self.assert_invalid('name: example\ndescription: Useful.\n' + extra, 'metadata|compatibility|license|allowed-tools')

    def test_frontmatter_must_be_delimited_mapping(self):
        for content in ('name: example\ndescription: Useful.', '---\nname: example', '---\n- example\n---\n'):
            with self.subTest(content=content):
                (self.skill / 'SKILL.md').write_text(content)
                with self.assertRaises(validator.MetadataError):
                    validator.validate_skill(self.skill)

    def test_local_resource_checks_ignore_code_and_external_urls(self):
        self.write(body='[Reference](details.md)\n[Remote](https://example.invalid/a)\n[Mail](mailto:person@example.invalid)\n```md\n[Example](missing.md)\n```\n')
        with self.assertRaisesRegex(validator.MetadataError, 'missing local resource'):
            validator.validate_skill(self.skill)
        (self.skill / 'details.md').write_text('A real resource.')
        validator.validate_skill(self.skill)

    def test_host_ui_mapping_is_checked_only_when_present(self):
        self.write()
        directory = self.skill / 'agents'
        directory.mkdir()
        path = directory / 'openai.yaml'
        for content in ('interface: []', 'interface:\n  display_name: false',
                        'policy:\n  allow_implicit_invocation: "false"', 'dependencies: []'):
            with self.subTest(content=content):
                path.write_text(content)
                with self.assertRaises(validator.MetadataError):
                    validator.validate_skill(self.skill)
        path.write_text('interface:\n  display_name: "Example"\npolicy:\n  allow_implicit_invocation: false\n')
        validator.validate_skill(self.skill)

    def test_cli_reports_invalid_skill_with_nonzero_exit(self):
        self.write('name: example\ndescription: false')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/validate_skills.py'), str(self.skill)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('description', result.stderr)


if __name__ == '__main__':
    unittest.main()
