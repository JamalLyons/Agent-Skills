"""Replanning reports managed scope drift before any simulated GitHub write."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from test_epic import FakeGitHub, base_plan, new_epic_plan, run_apply  # noqa: E402


class ScopeDriftTests(unittest.TestCase):
    def applied(self, data=None):
        gh = FakeGitHub()
        data = data or base_plan()
        code, report, err = run_apply(gh, data, '--execute')
        self.assertEqual(code, 0, err)
        gh.writes.clear()
        return gh, data, report

    def test_same_title_changed_acceptance_blocks_before_writes(self):
        gh, data, original = self.applied()
        issue = gh.issues[original['tasks']['T1']]
        before = copy.deepcopy(issue)
        data['tasks'][0]['acceptance'] = ['GET /x returns JSON with stable IDs']
        code, report, err = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertIn('scope drift', err)
        self.assertFalse(report['scope_reconciled'])
        drift = report['drift'][0]
        self.assertEqual((drift['task'], drift['issue']), ('T1', issue['number']))
        self.assertEqual(drift['sections']['Acceptance criteria'], {
            'current': '- [ ] GET /x returns 200',
            'proposed': '- [ ] GET /x returns JSON with stable IDs',
        })
        self.assertEqual(gh.writes, [])
        self.assertEqual(issue, before)

    def test_verification_drift_is_visible_in_dry_run(self):
        gh, data, _ = self.applied()
        data['tasks'][0]['verify'] = ['make integration-test']
        code, report, _ = run_apply(gh, data)
        self.assertEqual(code, 2)
        self.assertIn('make integration-test', report['drift'][0]['sections']['Verification']['proposed'])
        self.assertEqual(gh.writes, [])

    def test_custom_heading_in_generated_summary_is_compared(self):
        data = base_plan()
        data['tasks'][0]['summary'] = 'Existing endpoint\n\n## API behavior\nReturn CSV only.'
        gh, data, original = self.applied(data)
        before = gh.issues[original['tasks']['T1']]['body']
        data['tasks'][0]['summary'] = 'Existing endpoint\n\n## API behavior\nReturn CSV and PDF.'
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertEqual(report['drift'][0]['sections']['API behavior'], {
            'current': 'Return CSV only.', 'proposed': 'Return CSV and PDF.',
        })
        self.assertFalse(report['scope_reconciled'])
        self.assertEqual(gh.issues[original['tasks']['T1']]['body'], before)
        self.assertEqual(gh.writes, [])

    def test_removed_interior_custom_heading_is_not_mistaken_for_appended_notes(self):
        data = base_plan()
        data['tasks'][0]['summary'] = 'Existing endpoint\n\n## API behavior\nReturn CSV only.'
        gh, data, _ = self.applied(data)
        data['tasks'][0]['summary'] = 'Existing endpoint'
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertEqual(report['drift'][0]['sections']['API behavior']['proposed'], '')
        self.assertEqual(gh.writes, [])

    def test_removed_scope_section_is_not_silently_left_stale(self):
        data = base_plan()
        data['tasks'][0]['scope'] = ['Add the read endpoint']
        gh, data, _ = self.applied(data)
        data['tasks'][0]['scope'] = []
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertEqual(report['drift'][0]['sections']['Scope']['proposed'], '')
        self.assertEqual(gh.writes, [])

    def test_unchanged_rerun_accepts_resolved_dependency_numbers(self):
        gh, data, _ = self.applied()
        code, report, err = run_apply(gh, data, '--execute')
        self.assertEqual(code, 0, err)
        self.assertTrue(report['scope_reconciled'])
        self.assertEqual(report['drift'], [])
        self.assertEqual(gh.writes, [])

    def test_symbolic_dependency_display_normalizes_after_issue_creation(self):
        gh, data, original = self.applied()
        issue = gh.issues[original['tasks']['T2']]
        issue['body'] = issue['body'].replace(f'Blocked by #{original["tasks"]["T1"]}',
                                             'Blocked by T1 (new)')
        before = issue['body']
        code, report, err = run_apply(gh, data, '--execute')
        self.assertEqual(code, 0, err)
        self.assertEqual(report['drift'], [])
        self.assertEqual(issue['body'], before)
        self.assertEqual(gh.writes, [])

    def test_completion_marks_line_endings_marker_format_and_human_sections_survive(self):
        gh, data, original = self.applied()
        issue = gh.issues[original['tasks']['T1']]
        issue['body'] = (issue['body'].replace('- [ ]', '- [x]')
                         .replace('"v":1', '"v": 1')
                         .replace('\n', '  \r\n')
                         + '\r\n## Human discussion\r\nKeep this context exactly.\r\n')
        before = issue['body']
        code, report, err = run_apply(gh, data, '--execute')
        self.assertEqual(code, 0, err)
        self.assertEqual(report['drift'], [])
        self.assertEqual(issue['body'], before)
        self.assertEqual(gh.writes, [])

    def test_user_text_inside_managed_section_is_reported_not_deleted(self):
        gh, data, original = self.applied()
        issue = gh.issues[original['tasks']['T1']]
        issue['body'] = issue['body'].replace('GET /x returns 200',
                                             'GET /x returns 200\n- Human-added constraint')
        before = issue['body']
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertIn('Human-added constraint', report['drift'][0]['sections']['Acceptance criteria']['current'])
        self.assertEqual(issue['body'], before)
        self.assertEqual(gh.writes, [])

    def test_authorized_manual_reconciliation_then_rerun(self):
        gh, data, original = self.applied()
        data['tasks'][0]['acceptance'] = ['GET /x returns 201']
        self.assertEqual(run_apply(gh, data, '--execute')[0], 2)
        issue = gh.issues[original['tasks']['T1']]
        # Simulate a separately authorized manual edit, preserving marker/user text.
        issue['body'] = issue['body'].replace('GET /x returns 200', 'GET /x returns 201')
        issue['body'] += '\n## Operator notes\nPreserved after reconciliation.\n'
        before = issue['body']
        code, report, err = run_apply(gh, data)
        self.assertEqual(code, 0, err)
        self.assertTrue(report['scope_reconciled'])
        self.assertEqual(issue['body'], before)
        self.assertEqual(gh.writes, [])

    def test_root_scope_drift_blocks_new_tasks_before_writes(self):
        gh, data, original = self.applied(new_epic_plan())
        root = gh.issues[original['epic']]
        before = root['body']
        data['epic']['summary'] = 'Export both reports and invoices.'
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertEqual(report['drift'][0]['task'], 'epic')
        self.assertIn('Summary', report['drift'][0]['sections'])
        self.assertEqual(root['body'], before)
        self.assertEqual(gh.writes, [])

    def test_marker_tier_and_title_drift_are_explicit(self):
        gh, data, _ = self.applied()
        data['tasks'][0]['title'] = 'Add safer API'
        data['tasks'][0]['tier'] = 'easy'
        code, report, _ = run_apply(gh, data, '--execute')
        self.assertEqual(code, 2)
        self.assertIn('Title', report['drift'][0]['sections'])
        self.assertIn('Marker', report['drift'][0]['sections'])
        self.assertEqual(gh.writes, [])


if __name__ == '__main__':
    unittest.main()
