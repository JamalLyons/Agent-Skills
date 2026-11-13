"""Portable evaluation setup and adapter execution; no live agent/service calls."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('skill_evaluate', ROOT / 'scripts/evaluate.py')
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        skill = self.root / 'skills/example'
        (skill / 'evals/fixtures').mkdir(parents=True)
        (skill / 'references').mkdir()
        (skill / 'SKILL.md').write_text('---\nname: example\ndescription: Example fixture.\n---\nRead references/details.md.\n')
        (skill / 'references/details.md').write_text('Useful instruction.\n')
        (skill / 'evals/fixtures/input.txt').write_text('pinned input\n')
        self.path = skill / 'evals/evals.json'
        self.data = {'skill_name': 'example', 'evals': [{
            'id': 'ordinary', 'prompt': 'Summarize input.txt.',
            'expected_output': 'PRIVATE-GRADING-EXPECTATION',
            'files': ['evals/fixtures/input.txt'],
        }]}
        self.save()
        self.prepared = self.root / 'comparison'

    def save(self):
        self.path.write_text(json.dumps(self.data))

    def prepare(self):
        return evaluate.prepare(self.path, 'ordinary', self.prepared)

    def test_current_manifests_and_fixture_references_are_valid(self):
        paths = evaluate.manifests()
        expected = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')}
        self.assertEqual({p.parent.parent.name for p in paths}, expected)
        for path in paths:
            with self.subTest(manifest=path):
                evaluate.load_manifest(path)

    def test_rejects_traversal_absolute_missing_and_duplicate_fixtures(self):
        original = self.data['evals'][0]['files']
        for files in (['../SKILL.md'], [str(self.path)], ['missing.txt'], original * 2):
            with self.subTest(files=files):
                self.data['evals'][0]['files'] = files
                self.save()
                with self.assertRaises(evaluate.EvalError):
                    self.prepare()
                self.assertFalse(self.prepared.exists())

    def test_rejects_symlink_fixture_escape(self):
        outside = self.root / 'private.txt'
        outside.write_text('private')
        link = self.path.parent / 'fixtures/escape.txt'
        link.symlink_to(outside)
        self.data['evals'][0]['files'] = ['evals/fixtures/escape.txt']
        self.save()
        with self.assertRaises(evaluate.EvalError):
            self.prepare()

    def test_output_inside_skill_sources_is_rejected_before_snapshot(self):
        for output in (self.path.parent.parent / 'comparison', self.root / 'skills/other-result'):
            with self.subTest(output=output), self.assertRaisesRegex(evaluate.EvalError, 'outside the skills source tree'):
                evaluate.prepare(self.path, 'ordinary', output)
            self.assertFalse(output.exists())

    def test_prepare_is_pinned_separate_and_has_no_expected_answer_in_model_prompt(self):
        self.prepare()
        for variant in evaluate.VARIANTS:
            base = self.prepared / variant
            self.assertEqual((base / 'workspace/evals/fixtures/input.txt').read_text(), 'pinned input\n')
            self.assertNotIn('PRIVATE-GRADING-EXPECTATION', (base / 'prompt.txt').read_text())
            self.assertEqual((base / 'workspace/_skills').exists(), variant == 'with_skill')
        snapshot = self.prepared / 'with_skill/workspace/_skills/example'
        self.assertTrue((snapshot / 'references/details.md').is_file())
        self.assertFalse((snapshot / 'evals').exists())
        info = json.loads((self.prepared / 'case.json').read_text())
        self.assertEqual(info['fixture_sha256']['evals/fixtures/input.txt'], evaluate.digest(self.path.parent / 'fixtures/input.txt'))
        self.assertIsNone(info['semantic_grade'])
        (self.prepared / 'without_skill/workspace/evals/fixtures/input.txt').write_text('changed')
        self.assertEqual((self.prepared / 'with_skill/workspace/evals/fixtures/input.txt').read_text(), 'pinned input\n')

    def test_refuses_to_overwrite_comparison_or_rerun_a_variant(self):
        self.prepare()
        with self.assertRaises(evaluate.EvalError):
            self.prepare()
        adapter = [sys.executable, '-c', 'print("result")', '{prompt_file}']
        evaluate.run_variant(self.prepared, 'without_skill', adapter, 2, 'stub', 'stub')
        with self.assertRaises(evaluate.EvalError):
            evaluate.run_variant(self.prepared, 'without_skill', adapter, 2, 'stub', 'stub')

    def test_execution_is_not_a_grade_and_argv_is_not_shell_evaluated(self):
        self.prepare()
        literal = '$(touch NEVER-CREATED); echo shell'
        adapter = [sys.executable, '-c', 'import sys; print(sys.argv[2])', '{prompt_file}', literal]
        result = evaluate.run_variant(self.prepared, 'with_skill', adapter, 2, 'stub-host', 'stub-model')
        self.assertEqual(result['execution_status'], 'completed')
        self.assertIsNone(result['semantic_grade'])
        self.assertEqual(result['host'], 'stub-host')
        self.assertEqual((self.prepared / 'with_skill/stdout.log').read_text().strip(), literal)
        self.assertFalse((self.prepared / 'with_skill/workspace/NEVER-CREATED').exists())

    def test_nonzero_error_and_launch_failure_are_recorded(self):
        self.prepare()
        result = evaluate.run_variant(self.prepared, 'with_skill', [sys.executable, '-c', 'import sys; print("bad", file=sys.stderr); sys.exit(7)', '{prompt_file}'], 2, 'stub', 'stub')
        self.assertEqual(result['execution_status'], 'failed')
        self.assertEqual(result['exit_code'], 7)
        self.assertIsNone(result['semantic_grade'])
        self.assertIn('bad', (self.prepared / 'with_skill/stderr.log').read_text())
        result = evaluate.run_variant(self.prepared, 'without_skill', ['/does/not/exist', '{prompt_file}'], 2, 'stub', 'stub')
        self.assertEqual(result['execution_status'], 'launch_failed')
        self.assertIsNone(result['semantic_grade'])

    def test_timeout_preserves_partial_output_and_does_not_claim_pass(self):
        self.prepare()
        adapter = [sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)', '{prompt_file}']
        result = evaluate.run_variant(self.prepared, 'with_skill', adapter, .1, 'stub', 'stub')
        self.assertEqual(result['execution_status'], 'timed_out')
        self.assertIsNone(result['semantic_grade'])
        self.assertIn('started', (self.prepared / 'with_skill/stdout.log').read_text())

    def test_invalid_adapter_or_timeout_cannot_start_execution(self):
        self.prepare()
        for adapter, timeout in (([], 1), ('echo hi', 1), (['echo'], 1), (['echo', '{prompt_file}'], float('nan')), (['echo', '{prompt_file}'], 0)):
            with self.subTest(adapter=adapter, timeout=timeout), self.assertRaises(evaluate.EvalError):
                evaluate.run_variant(self.prepared, 'with_skill', adapter, timeout, 'stub', 'stub')
        self.assertFalse((self.prepared / 'with_skill/run.json').exists())

    def test_bad_case_identity_is_rejected(self):
        for key in ('../escape', '', 'a/b'):
            self.data['evals'][0]['id'] = key
            self.save()
            with self.assertRaises(evaluate.EvalError):
                evaluate.load_manifest(self.path)

    def test_cli_validation_runs_without_an_adapter(self):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/evaluate.py'), 'validate', '--manifest', str(self.path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no agent evaluations executed', result.stdout)


if __name__ == '__main__':
    unittest.main()
