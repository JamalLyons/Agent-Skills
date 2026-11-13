"""Check discoverable skill packages and real installer behavior without user state."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SKILLS = sorted(p for p in (REPO / "skills").iterdir() if (p / "SKILL.md").is_file())
spec = importlib.util.spec_from_file_location('validate_skills', REPO / 'scripts/validate_skills.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


class PackagingTests(unittest.TestCase):
    def test_skill_identity_and_local_resources(self):
        for skill in SKILLS:
            with self.subTest(skill=skill.name):
                validator.validate_skill(skill)

    def test_install_all_resources_twice_and_prune_deleted_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets = [Path(tmp) / "claude", Path(tmp) / "agents"]
            for target in targets:
                target.mkdir()
                (target / "deleted-skill").symlink_to(REPO / "skills" / "deleted-skill")
                (target / "unrelated").symlink_to(Path(tmp) / "unrelated-source")
            command = ["bash", str(REPO / "install.sh")]
            for target in targets:
                command += ["--target", str(target)]
            for _ in range(2):
                subprocess.run(command, check=True, capture_output=True, text=True)
                for target in targets:
                    self.assertFalse((target / "deleted-skill").is_symlink())
                    self.assertTrue((target / "unrelated").is_symlink())
                    for skill in SKILLS:
                        link = target / skill.name
                        self.assertTrue(link.is_symlink())
                        self.assertEqual(link.resolve(), skill)
                        for resource in skill.rglob("*"):
                            if resource.is_file():
                                installed = link / resource.relative_to(skill)
                                self.assertEqual(installed.read_bytes(), resource.read_bytes())

    def test_installer_preserves_real_directory_on_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp) / SKILLS[0].name
            existing.mkdir()
            marker = existing / "keep.txt"
            marker.write_text("user-owned")
            result = subprocess.run(
                ["bash", str(REPO / "install.sh"), "--target", tmp],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertFalse(existing.is_symlink())
            self.assertEqual(marker.read_text(), "user-owned")


if __name__ == "__main__":
    unittest.main()
