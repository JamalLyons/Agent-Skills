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


    def ran(self, *variants, usage=None):
        self.prepare()
        for variant in variants:
            script = 'import json, sys; print("artifact")'
            if usage is not None and variant == 'with_skill':
                script += f'; open(sys.argv[2] + "/usage.json", "w").write({json.dumps(json.dumps(usage))})'
            evaluate.run_variant(self.prepared, variant, [sys.executable, '-c', script, '{prompt_file}', '{output_dir}'], 5, 'stub', 'stub-model')

    def note(self, *results):
        return {'grader': 'tester', 'limitations': ['stub adapter only'],
                'assertions': [{'id': f'a{i}', 'result': r, 'evidence': f'saw {r}'} for i, r in enumerate(results)]}

    def test_grade_records_structured_note_next_to_case(self):
        self.ran('with_skill')
        entry = evaluate.grade(self.prepared, 'with_skill', self.note('pass', 'partial', 'fail', 'pass'))
        self.assertEqual(entry['score'], 0.625)
        saved = json.loads((self.prepared / 'grades.json').read_text())
        self.assertEqual(saved['variants']['with_skill']['assertions'][1]['result'], 'partial')
        self.assertFalse(saved['variants']['with_skill']['blind'])
        self.assertIsNone(json.loads((self.prepared / 'with_skill/run.json').read_text())['semantic_grade'])

    def test_grade_refuses_unrun_variant_bad_schema_duplicates_and_mismatched_assertions(self):
        self.ran('with_skill')
        with self.assertRaisesRegex(evaluate.EvalError, 'never ran'):
            evaluate.grade(self.prepared, 'without_skill', self.note('pass'))
        bad_notes = [[], {'assertions': []}, {**self.note('pass'), 'grader': ''},
                     {**self.note('pass'), 'extra': 1}, {**self.note('pass'), 'limitations': 'none'},
                     {'grader': 'x', 'limitations': [], 'assertions': [{'id': 'a', 'result': 'ok', 'evidence': 'e'}]},
                     {'grader': 'x', 'limitations': [], 'assertions': [{'id': 'a', 'result': 'pass', 'evidence': ' '}]},
                     {'grader': 'x', 'limitations': [], 'assertions': [{'id': 'a', 'result': 'pass', 'evidence': 'e'}] * 2}]
        for note in bad_notes:
            with self.subTest(note=note), self.assertRaises(evaluate.EvalError):
                evaluate.grade(self.prepared, 'with_skill', note)
        self.assertFalse((self.prepared / 'grades.json').exists())
        evaluate.grade(self.prepared, 'with_skill', self.note('pass'))
        with self.assertRaisesRegex(evaluate.EvalError, 'already graded'):
            evaluate.grade(self.prepared, 'with_skill', self.note('fail'))
        self.assertEqual(evaluate.grade(self.prepared, 'with_skill', self.note('fail'), replace=True)['score'], 0)
        evaluate.run_variant(self.prepared, 'without_skill', [sys.executable, '-c', '', '{prompt_file}'], 5, 'stub', 'stub-model')
        with self.assertRaisesRegex(evaluate.EvalError, 'must match'):
            evaluate.grade(self.prepared, 'without_skill', self.note('pass', 'pass'))

    def test_launch_failure_cannot_be_graded(self):
        self.prepare()
        evaluate.run_variant(self.prepared, 'with_skill', ['/does/not/exist', '{prompt_file}'], 2, 'stub', 'stub')
        with self.assertRaisesRegex(evaluate.EvalError, 'never ran'):
            evaluate.grade(self.prepared, 'with_skill', self.note('pass'))

    def test_blind_packet_hides_variant_and_grades_resolve_through_key(self):
        self.ran('with_skill')
        with self.assertRaisesRegex(evaluate.EvalError, 'has not run'):
            evaluate.blind(self.prepared)
        evaluate.run_variant(self.prepared, 'without_skill', [sys.executable, '-c', 'print("artifact")', '{prompt_file}'], 5, 'stub', 'stub-model')
        packet = evaluate.blind(self.prepared, seed=3)
        self.assertEqual(sorted(p.name for p in packet.iterdir()), ['A', 'B'])
        for label in evaluate.LABELS:
            self.assertFalse((packet / label / 'workspace/_skills').exists())
            self.assertFalse((packet / label / 'prompt.txt').exists())
            self.assertTrue((packet / label / 'workspace/evals/fixtures/input.txt').is_file())
        with self.assertRaises(evaluate.EvalError):
            evaluate.blind(self.prepared)
        key = json.loads((self.prepared / 'blind-key.json').read_text())['labels']
        entry = evaluate.grade(self.prepared, None, self.note('pass'), label='A')
        self.assertTrue(entry['blind'])
        self.assertIn(key['A'], json.loads((self.prepared / 'grades.json').read_text())['variants'])

    def test_report_aggregates_without_fabricating_missing_numbers(self):
        self.ran('with_skill', 'without_skill', usage={'input_tokens': 100, 'output_tokens': 20})
        evaluate.grade(self.prepared, 'with_skill', self.note('pass', 'pass'))
        evaluate.grade(self.prepared, 'without_skill', self.note('pass', 'fail'))
        second = self.root / 'runs/second'
        evaluate.prepare(self.path, 'ordinary', second)
        evaluate.run_variant(second, 'with_skill', [sys.executable, '-c', '', '{prompt_file}'], 5, 'stub', 'stub-model')
        summary = evaluate.report([self.prepared, self.root / 'runs'])
        skill = summary['skills']['example']
        self.assertEqual(skill['comparisons'], 2)
        self.assertEqual(skill['paired'], 1)
        self.assertEqual(skill['score_delta'], 0.5)
        w, wo = skill['variants']['with_skill'], skill['variants']['without_skill']
        self.assertEqual((w['ran'], w['graded'], w['ungraded']), (2, 1, 1))
        self.assertEqual((wo['ran'], wo['graded'], wo['ungraded']), (1, 1, 0))
        self.assertEqual((w['mean_tokens'], w['tokens_reported']), (120, 1))
        self.assertIsNone(wo['mean_tokens'])
        self.assertIsNotNone(w['mean_elapsed_seconds'])
        markdown = evaluate.report_markdown(summary)
        self.assertIn('## example', markdown)
        self.assertIn('n/a (0)', markdown)
        self.assertIn('not_run', markdown)

    def test_report_ignores_malformed_usage_and_flags_mismatched_models(self):
        self.ran('with_skill', usage={'input_tokens': '5', 'output_tokens': 1})
        evaluate.run_variant(self.prepared, 'without_skill', [sys.executable, '-c', '', '{prompt_file}'], 5, 'stub', 'other-model')
        skill = evaluate.report([self.prepared])['skills']['example']
        self.assertIsNone(skill['variants']['with_skill']['mean_tokens'])
        self.assertIsNone(skill['score_delta'])
        self.assertTrue(any('different host/model' in w for w in skill['warnings']))

    def test_cli_grade_and_report(self):
        self.ran('with_skill')
        note = self.root / 'note.json'
        note.write_text(json.dumps(self.note('partial')))
        script = str(ROOT / 'scripts/evaluate.py')
        result = subprocess.run([sys.executable, script, 'grade', str(self.prepared), '--variant', 'with_skill', '--note', str(note)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, script, 'grade', str(self.prepared), '--variant', 'without_skill', '--note', str(note)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        out = self.root / 'summary'
        result = subprocess.run([sys.executable, script, 'report', str(self.prepared), '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(Path(f'{out}.json').read_text())['skills']['example']['variants']['with_skill']['mean_score'], 0.5)
        self.assertIn('# Skill evaluation report', Path(f'{out}.md').read_text())

if __name__ == '__main__':
    unittest.main()
