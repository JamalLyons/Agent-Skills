"""Duplicate-marker recovery is explicit and works for closed extras as documented."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from epiclib import parse_epic_marker, parse_marker, render_body, render_epic_body, validate_plan  # noqa: E402
from test_epic import FakeGitHub, base_plan, new_epic_plan, run_apply  # noqa: E402


class MarkerRecoveryTests(unittest.TestCase):
    def task_duplicates(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        plan = validate_plan(base_plan())
        body = render_body(plan, plan.by_key['T1'], {})
        canonical = gh.add_issue('Add API', body, labels=['workforce'])
        extra = gh.add_issue('Add API', body, labels=['workforce'], state='closed')
        return gh, canonical, extra

    def epic_duplicates(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        body = render_epic_body(validate_plan(new_epic_plan()))
        canonical = gh.add_issue('CSV export', body, labels=['workforce'])
        extra = gh.add_issue('CSV export', body, labels=['workforce'], state='closed')
        return gh, canonical, extra

    def test_closed_task_duplicate_still_blocks_before_writes(self):
        gh, canonical, extra = self.task_duplicates()
        code, _, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('closing extras does not resolve marker identity', err)
        self.assertIn('explicit authorization', err)
        self.assertIn('workforce-epic-superseded', err)
        self.assertEqual(gh.writes, [])
        self.assertIsNotNone(parse_marker(canonical['body']))
        self.assertIsNotNone(parse_marker(extra['body']))

    def test_closed_epic_duplicate_still_blocks_before_writes(self):
        gh, canonical, extra = self.epic_duplicates()
        code, _, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('closing extras does not resolve marker identity', err)
        self.assertIn('workforce-epic-root-superseded', err)
        self.assertEqual(gh.writes, [])
        self.assertIsNotNone(parse_epic_marker(canonical['body']))
        self.assertIsNotNone(parse_epic_marker(extra['body']))

    def test_authorized_manual_task_marker_rename_reuses_canonical(self):
        gh, canonical, extra = self.task_duplicates()
        # Simulate only the issue-body edit explicitly authorized in the procedure.
        original = extra['body']
        extra['body'] = original.replace('<!-- workforce-epic:',
                                         '<!-- workforce-epic-superseded:', 1)
        self.assertIsNone(parse_marker(extra['body']))
        self.assertEqual(extra['body'].replace('<!-- workforce-epic-superseded:',
                                               '<!-- workforce-epic:'), original)
        code, report, err = run_apply(gh, base_plan())
        self.assertEqual(code, 0, err)
        self.assertEqual(report['tasks']['T1'], canonical['number'])
        self.assertFalse(any(a['action'] == 'create' and a['task'] == 'T1'
                             for a in report['actions']))
        self.assertEqual(gh.writes, [])

    def test_authorized_manual_epic_marker_rename_reuses_canonical(self):
        gh, canonical, extra = self.epic_duplicates()
        original = extra['body']
        extra['body'] = original.replace('<!-- workforce-epic-root:',
                                         '<!-- workforce-epic-root-superseded:', 1)
        self.assertIsNone(parse_epic_marker(extra['body']))
        self.assertEqual(extra['body'].replace('<!-- workforce-epic-root-superseded:',
                                               '<!-- workforce-epic-root:'), original)
        code, report, err = run_apply(gh, new_epic_plan())
        self.assertEqual(code, 0, err)
        self.assertEqual(report['epic'], canonical['number'])
        self.assertFalse(any(a['action'] == 'epic' for a in report['actions']))
        self.assertEqual(gh.writes, [])


if __name__ == '__main__':
    unittest.main()
