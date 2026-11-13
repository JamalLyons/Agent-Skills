"""Persistent transition invariants, without pretending to control a live agent host."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'run_state.py'
spec = importlib.util.spec_from_file_location('run_state', SCRIPT)
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)
BASE, HEAD, INTEGRATED = 'a' * 40, 'b' * 40, 'c' * 40


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.state = rs.apply_event(rs.new_state('run-1', 'example/repo', ['example/repo#1']),
                                    {'type': 'claim'}, 'lead-1')
        self.state = self.event(type='add-step', step='S1', base=BASE, checkout='/fixture')

    def event(self, **event):
        self.state = rs.apply_event(self.state, event, 'lead-1')
        return self.state

    def start(self, **extra):
        return self.event(type='transition', step='S1', to='running', attempt_id='A1', **extra)

    def accept(self, step='S1', head=HEAD):
        self.event(type='transition', step=step, to='verifying')
        self.event(type='transition', step=step, to='accepted', head=head,
                   evidence=['Observed fixture test: python -m unittest, exit 0'])

    def test_restart_retains_accepted_artifact_and_rejects_duplicate_integration(self):
        self.start()
        self.accept()
        self.state = json.loads(json.dumps(self.state))
        self.event(type='transition', step='S1', to='integrated', source_head=HEAD, head=INTEGRATED)
        before = deepcopy(self.state)
        with self.assertRaisesRegex(rs.StateError, 'invalid transition'):
            self.event(type='transition', step='S1', to='integrated', source_head=HEAD, head=INTEGRATED)
        self.assertEqual(self.state, before)

    def test_same_source_cannot_be_integrated_as_another_step(self):
        self.start()
        self.accept()
        self.event(type='transition', step='S1', to='integrated', source_head=HEAD, head=INTEGRATED)
        self.event(type='add-step', step='S2', base=BASE, checkout='/fixture')
        self.event(type='transition', step='S2', to='running', attempt_id='A2')
        self.accept(step='S2')
        with self.assertRaisesRegex(rs.StateError, 'source head already integrated'):
            self.event(type='transition', step='S2', to='integrated', source_head=HEAD, head='d' * 40)

    def test_runtime_task_needs_terminal_observation_before_another_writer(self):
        self.start(task_id='task-123')
        with self.assertRaisesRegex(rs.StateError, 'host terminal status'):
            self.event(type='transition', step='S1', to='verifying')
        self.event(type='transition', step='S1', to='waiting')
        summary = rs.status(self.state)
        self.assertEqual(summary['active_observations_to_reconcile']['S1']['attempt']['task_id'], 'task-123')
        self.assertEqual(summary['actionable_after_reconciliation'], [])
        self.event(type='transition', step='S1', to='verifying', terminal_status='completed',
                   terminal_evidence='Host task read returned completed for task-123')
        self.assertEqual(self.state['steps']['S1']['status'], 'verifying')

    def test_acceptance_requires_head_and_independent_evidence(self):
        self.start()
        self.event(type='transition', step='S1', to='verifying')
        for head, evidence in ((None, ['test passed']), (HEAD, []), (HEAD, [''])):
            with self.subTest(head=head, evidence=evidence), self.assertRaises(rs.StateError):
                self.event(type='transition', step='S1', to='accepted', head=head, evidence=evidence)

    def test_attempt_identity_is_not_reused_on_rework(self):
        self.start()
        self.event(type='transition', step='S1', to='rework', reason='Observed failing case')
        with self.assertRaisesRegex(rs.StateError, 'new attempt identity'):
            self.start()
        self.event(type='transition', step='S1', to='running', attempt_id='A2')
        self.assertEqual(len(self.state['steps']['S1']['attempts']), 2)

    def test_prerequisite_blocks_dispatch(self):
        self.event(type='add-step', step='S2', base=BASE, checkout='/fixture', dependencies=['S1'])
        with self.assertRaisesRegex(rs.StateError, 'prerequisites'):
            self.event(type='transition', step='S2', to='running', attempt_id='A2')

    def test_active_writer_excludes_another_step_in_same_checkout(self):
        self.start()
        self.event(type='add-step', step='S2', base=BASE, checkout='/fixture')
        with self.assertRaisesRegex(rs.StateError, 'another active writer'):
            self.event(type='transition', step='S2', to='running', attempt_id='A2')

    def test_runtime_task_cannot_be_assigned_to_two_active_steps(self):
        self.start(task_id='host/task-1')
        self.event(type='add-step', step='S2', base=BASE, checkout='/other-fixture')
        with self.assertRaisesRegex(rs.StateError, 'runtime task already assigned'):
            self.event(type='transition', step='S2', to='running', attempt_id='A2', task_id='host/task-1')

    def test_unanswered_followups_survive_resume_and_need_decision_to_drop(self):
        self.event(type='followup', id='F1', values={'problem': 'Failure remains',
            'evidence': 'Reviewer inspected fixture:12', 'pending_question': 'Open an issue?',
            'tracking': 'untracked'})
        self.state = json.loads(json.dumps(self.state))
        self.assertIn('F1', rs.status(self.state)['unanswered_followups'])
        with self.assertRaisesRegex(rs.StateError, 'recorded user decision'):
            self.event(type='followup', id='F1', values={'outcome': 'dropped'})
        self.assertIn('F1', rs.status(self.state)['unanswered_followups'])
        self.event(type='followup', id='F1', values={'outcome': 'dropped',
            'authorization': 'User said drop F1 in session message 9'})
        self.assertNotIn('F1', rs.status(self.state)['unanswered_followups'])

    def test_conflicting_owner_cannot_claim_or_change_state(self):
        for event in ({'type': 'claim'}, {'type': 'release'}):
            with self.assertRaisesRegex(rs.StateError, 'run owned by lead-1'):
                rs.apply_event(self.state, event, 'lead-2')
        self.event(type='release')
        resumed = rs.apply_event(self.state, {'type': 'claim'}, 'lead-2')
        self.assertEqual(resumed['owner'], 'lead-2')

    def test_version_and_dependency_validation(self):
        broken = deepcopy(self.state)
        broken['version'] = 999
        with self.assertRaisesRegex(rs.StateError, 'version'):
            rs.validate(broken)
        broken = deepcopy(self.state)
        broken['steps']['S1']['dependencies'] = ['missing']
        with self.assertRaisesRegex(rs.StateError, 'dependencies'):
            rs.validate(broken)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'state.json'
        rs.atomic_write(self.path, rs.new_state('r', 'example/repo'))

    def test_failed_replace_preserves_old_file_and_cleans_temporary(self):
        before = self.path.read_bytes()
        with patch.object(rs.os, 'replace', side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):
                rs.mutate(self.path, {'type': 'claim'}, 'lead')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_rejected_event_and_stale_revision_preserve_file(self):
        before = self.path.read_bytes()
        with self.assertRaises(rs.StateError):
            rs.mutate(self.path, {'type': 'release'}, 'lead')
        self.assertEqual(self.path.read_bytes(), before)
        rs.mutate(self.path, {'type': 'claim'}, 'lead', expected_revision=0)
        before = self.path.read_bytes()
        with self.assertRaisesRegex(rs.StateError, 'revision changed'):
            rs.mutate(self.path, {'type': 'release'}, 'lead', expected_revision=0)
        self.assertEqual(self.path.read_bytes(), before)

    def test_local_lock_excludes_another_writer_without_stealing_lock(self):
        lock = self.path.with_name(self.path.name + '.lock')
        lock.write_text('existing writer')
        with self.assertRaisesRegex(rs.StateError, 'writer lock exists'):
            rs.mutate(self.path, {'type': 'claim'}, 'lead')
        self.assertEqual(lock.read_text(), 'existing writer')

    def test_cli_init_apply_and_status_across_processes(self):
        path = Path(self.temp.name) / 'new' / 'state.json'
        def run(*args, stdin=None):
            return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                                  text=True, capture_output=True)
        result = run('init', str(path), '--run-id', 'r1', '--repository', 'example/repo')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = run('apply', str(path), '--owner', 'lead', '--event', '-', stdin='{"type":"claim"}')
        self.assertEqual(result.returncode, 0, result.stderr)
        result = run('status', str(path))
        self.assertEqual(json.loads(result.stdout)['owner'], 'lead')
        result = run('init', str(path), '--run-id', 'r2', '--repository', 'other/repo')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(rs.load(path)['run_id'], 'r1')


if __name__ == '__main__':
    unittest.main()
