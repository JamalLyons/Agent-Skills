"""Installer ownership and preview behavior, always using disposable targets."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
INSTALLER = REPO / 'install.sh'
SKILLS = sorted(path for path in (REPO / 'skills').iterdir() if (path / 'SKILL.md').is_file())


class InstallerCollisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'target'
        self.target.mkdir()
        self.skill = SKILLS[0]
        self.link = self.target / self.skill.name

    def install(self, *options, target=None):
        return subprocess.run(
            ['bash', str(INSTALLER), '--target', str(target or self.target), *options],
            capture_output=True, text=True,
        )

    def snapshot(self):
        return {
            str(path.relative_to(self.root)): ('link', os.readlink(path)) if path.is_symlink()
            else ('directory',) if path.is_dir() else ('file', path.read_bytes())
            for path in self.root.rglob('*')
        }

    def test_valid_foreign_link_is_preserved_until_explicit_replacement(self):
        foreign = self.root / 'other-collection'
        foreign.mkdir()
        marker = foreign / 'keep.txt'
        marker.write_text('user-owned')
        self.link.symlink_to(foreign)
        result = self.install()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.link.resolve(), foreign)
        self.assertIn('foreign symlink preserved', result.stderr)
        result = self.install('--replace-links')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.link.resolve(), self.skill)
        self.assertEqual(marker.read_text(), 'user-owned')

    def test_broken_foreign_link_is_not_pruned_or_replaced_by_default(self):
        missing = self.root / 'foreign-missing'
        self.link.symlink_to(missing)
        result = self.install()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(self.link.is_symlink())
        self.assertEqual(os.readlink(self.link), str(missing))
        result = self.install('--replace-links')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.link.resolve(), self.skill)

    def test_relative_correct_link_is_kept_without_rewriting_it(self):
        relative = os.path.relpath(self.skill, self.target)
        self.link.symlink_to(relative)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(os.readlink(self.link), relative)
        self.assertIn(f'ok      {self.skill.name}', result.stdout)

    def test_owned_link_pointing_at_another_skill_is_refreshed(self):
        self.link.symlink_to(SKILLS[1])
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.link.resolve(), self.skill)

    def test_only_owned_broken_links_are_pruned_including_relative_links(self):
        owned = self.target / 'deleted-owned-skill'
        owned.symlink_to(os.path.relpath(REPO / 'skills/deleted-owned-skill', self.target))
        foreign = self.target / 'deleted-foreign-skill'
        foreign.symlink_to(self.root / 'missing-foreign-skill')
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(owned.is_symlink())
        self.assertTrue(foreign.is_symlink())

    def test_real_files_and_directories_survive_replace_flag(self):
        for as_directory in (False, True):
            with self.subTest(directory=as_directory):
                if self.link.exists():
                    self.link.unlink()
                if as_directory:
                    self.link.mkdir()
                    marker = self.link / 'keep.txt'
                else:
                    marker = self.link
                marker.write_text('keep')
                result = self.install('--replace-links')
                self.assertEqual(result.returncode, 1)
                self.assertFalse(self.link.is_symlink())
                self.assertEqual(marker.read_text(), 'keep')

    def test_dry_run_does_not_create_missing_target_or_its_parents(self):
        missing = self.root / 'absent/also-absent/skills'
        before = self.snapshot()
        result = self.install('--dry-run', target=missing)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(missing.parent.exists())
        self.assertEqual(self.snapshot(), before)
        self.assertIn('would create directory', result.stdout)
        self.assertIn('Dry run: no files changed', result.stdout)

    def test_dry_run_preserves_existing_links_even_with_replace_flag(self):
        foreign = self.root / 'foreign'
        foreign.mkdir()
        self.link.symlink_to(foreign)
        (self.target / 'deleted-skill').symlink_to(REPO / 'skills/deleted-skill')
        before = self.snapshot()
        result = self.install('--dry-run', '--replace-links')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot(), before)
        self.assertIn('would relink', result.stdout)
        self.assertIn('would prune', result.stdout)

    def test_non_directory_target_is_reported_without_modification(self):
        target = self.root / 'not-a-directory'
        target.write_text('keep')
        for options in ((), ('--dry-run', '--replace-links')):
            with self.subTest(options=options):
                result = self.install(*options, target=target)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(target.read_text(), 'keep')
                self.assertIn('destination exists and is not a directory', result.stderr)


if __name__ == '__main__':
    unittest.main()
