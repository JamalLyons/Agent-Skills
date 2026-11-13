"""Ownership warnings must cover future files as well as existing paths."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from epiclib import paths_overlap, validate_plan  # noqa: E402


class OwnershipOverlapTests(unittest.TestCase):
    def assert_overlap(self, a, b, expected=True):
        self.assertEqual(paths_overlap(a, b), expected, (a, b))
        self.assertEqual(paths_overlap(b, a), expected, (b, a))

    def test_partial_filename_globs_cover_literal_files(self):
        for pattern in ('src/foo*.ts', 'src/foo?.ts', 'src/foo[ab].ts'):
            with self.subTest(pattern=pattern):
                self.assert_overlap(pattern, 'src/foob.ts')
        self.assert_overlap('src/foo*.ts', 'src/foobar.ts')

    def test_literal_ownership_includes_descendants(self):
        self.assert_overlap('src/foo', 'src/foo/new/file.ts')
        self.assert_overlap('src/foo/', 'src/foo*.ts')
        self.assert_overlap('src', 'src/foo*.ts')
        self.assert_overlap('src/fo', 'src/foo*.ts', False)
        self.assert_overlap('src/foo', 'src/foobar', False)

    def test_directory_and_future_file_globs(self):
        self.assert_overlap('src/foo*/', 'src/foobar/future.ts')
        self.assert_overlap('src/**/x.ts', 'src/y.ts')
        self.assert_overlap('src/*', 'src2/new.ts', False)
        self.assert_overlap('src/foo/*', 'src/foobar/new.ts', False)

    def test_potential_glob_intersections_are_conservative(self):
        self.assert_overlap('src/foo*.ts', 'src/foobar?.ts')
        self.assert_overlap('src/foo[ab].ts', 'src/foo[cd].ts')
        self.assert_overlap('src/**/a.ts', 'src/new/**/b.ts')
        self.assert_overlap('src/foo*.ts', 'src/bar*.ts', False)
        self.assert_overlap('src/*', 'src2/*', False)

    def test_root_and_bare_globs_cannot_claim_disjoint_ownership(self):
        for root in ('', '.', './', '*', '**', '*.md'):
            with self.subTest(root=root):
                self.assert_overlap(root, 'src/future.ts')

    def test_equivalent_repository_paths_are_normalized(self):
        self.assert_overlap('./src//foo/', 'src/foo/future.ts')
        self.assert_overlap('src\\foo\\*.ts', './src/foo/future.ts')
        self.assert_overlap('./src/foo*.ts', 'src/foobar.ts')

    def test_outside_paths_do_not_establish_safe_parallel_ownership(self):
        for outside in ('../other', 'src/../other', '/tmp/other', 'C:\\other'):
            with self.subTest(outside=outside):
                self.assert_overlap(outside, 'src/future.ts')

    @staticmethod
    def plan(a, b, ordered=False):
        return {
            'version': 1, 'repo': 'acme/app', 'epic': 1,
            'criteria': [{'id': 'C1', 'text': 'Behavior works', 'covered_by': ['T1', 'T2']}],
            'tasks': [
                {'key': 'T1', 'title': 'First', 'tier': 'easy', 'summary': 'First slice',
                 'owned_paths': [a], 'acceptance': ['First behavior works'], 'verify': ['make test']},
                {'key': 'T2', 'title': 'Second', 'tier': 'easy', 'summary': 'Second slice',
                 'owned_paths': [b], 'acceptance': ['Second behavior works'], 'verify': ['make test'],
                 'blocked_by': ['T1'] if ordered else []},
            ],
        }

    def test_validator_warns_for_partial_glob_collision(self):
        plan = validate_plan(self.plan('src/foo*.ts', 'src/foobar.ts'))
        self.assertTrue(any('cannot run in parallel' in warning for warning in plan.warnings))

    def test_validator_allows_disjoint_or_ordered_ownership(self):
        for plan in (self.plan('src/foo*.ts', 'src/bar*.ts'),
                     self.plan('src/foo*.ts', 'src/foobar.ts', ordered=True)):
            with self.subTest(plan=plan):
                self.assertFalse(validate_plan(plan).warnings)


if __name__ == '__main__':
    unittest.main()
