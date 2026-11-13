"""Pinned destinations and input rejection with dummy data and a local gh stub."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

TEMPLATE = Path(__file__).resolve().parents[1] / "template.sh"


class DestinationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "intended project"
        self.other = Path(self.tmp.name) / "other checkout"
        self.bin = Path(self.tmp.name) / "bin"
        for path in (self.root, self.other, self.bin):
            path.mkdir()
        self.log = Path(self.tmp.name) / "gh-log.jsonl"
        gh = self.bin / "gh"
        gh.write_text(
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "with open(os.environ['WIZARD_TEST_LOG'], 'a') as f:\n"
            " f.write(json.dumps({'argv':sys.argv[1:], 'stdin':sys.stdin.read() if sys.argv[1:3]==['secret','set'] else ''})+'\\n')\n"
            "sys.exit(int(os.environ.get('WIZARD_TEST_GH_EXIT','0')))\n"
        )
        gh.chmod(0o755)

    def run_helper(self, script, input="", extra_env=None):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ["PATH"],
                   WIZARD_TEST_LOG=str(self.log))
        env.update(extra_env or {})
        return subprocess.run(
            ["bash", "-c", 'source "$1"; ' + script, "wizard-test", str(TEMPLATE), str(self.root)],
            cwd=self.other, env=env, input=input, capture_output=True, text=True,
        )

    def test_relative_env_is_anchored_to_explicit_project_root(self):
        result = self.run_helper('configure_destinations "$2" .env acme/intended; write_env DUMMY value')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / ".env").read_text(), "DUMMY='value'\n")
        self.assertFalse((self.other / ".env").exists())

    def test_unpinned_relative_env_is_rejected_without_creating_a_file(self):
        result = self.run_helper('ENV_FILE=.env; write_env DUMMY value')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / ".env").exists())
        self.assertFalse((self.other / ".env").exists())

    def test_invalid_project_root_fails_before_any_write(self):
        result = self.run_helper('configure_destinations . .env acme/intended; write_env DUMMY value')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.other / ".env").exists())

    def test_github_writes_always_name_pinned_repository(self):
        result = self.run_helper('configure_destinations "$2" .env acme/intended; set_secret DUMMY dummy-secret; set_var MODE test')
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        writes = [c for c in calls if c["argv"][:2] in (["secret", "set"], ["variable", "set"])]
        self.assertEqual(len(writes), 2)
        for call in writes:
            args = call["argv"]
            self.assertEqual(args[args.index("--repo") + 1], "acme/intended")
        secret = next(c for c in writes if c["argv"][0] == "secret")
        self.assertEqual(secret["stdin"], "dummy-secret")
        self.assertNotIn("dummy-secret", secret["argv"])
        self.assertNotIn("dummy-secret", result.stdout + result.stderr)

    def test_missing_github_repository_does_not_invoke_gh(self):
        result = self.run_helper('GITHUB_REPO=""; set_secret DUMMY dummy')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists())

    def test_env_read_failure_preserves_file_and_cleans_temporary_copy(self):
        env_file = self.root / ".env"
        env_file.write_text("DUMMY='saved-dummy'\nOTHER='keep'\n")
        grep = self.bin / "grep"
        grep.write_text("#!/usr/bin/env bash\nexit 2\n")
        grep.chmod(0o755)
        temp_files = self.root / "temporary files"
        temp_files.mkdir()
        result = self.run_helper('configure_destinations "$2" .env acme/intended; write_env DUMMY replacement',
                                 extra_env={"TMPDIR": str(temp_files)})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(env_file.read_text(), "DUMMY='saved-dummy'\nOTHER='keep'\n")
        self.assertEqual(list(temp_files.iterdir()), [])

    def test_partial_setup_is_reported_when_remote_write_skipped(self):
        result = self.run_helper('configure_destinations "$2" .env acme/intended; set_secret DUMMY dummy; finish',
                                 extra_env={"WIZARD_TEST_GH_EXIT": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Setup incomplete", result.stdout)
        self.assertNotIn("Setup complete", result.stdout)
        self.assertIn("--repo acme/intended", result.stdout)

    def test_template_without_destinations_stops_before_opening_browser(self):
        result = subprocess.run(["bash", str(TEMPLATE)], cwd=self.other,
                                stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse((self.other / ".env").exists())


class InputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_file = Path(self.tmp.name) / ".env"

    def ask(self, helper="ask_secret", input="", optional=False, before="", validator=""):
        command = (f'{before}; ' if before else "")
        command += f'{helper} DUMMY "Dummy value:" {"optional" if optional else "required"}'
        if validator:
            command += " " + validator
        command += '; printf "captured=<%s>" "$DUMMY"'
        return subprocess.run(
            ["bash", "-c", 'source "$1"; ENV_FILE="$2"; DUMMY=unchanged; ' + command,
             "input-test", str(TEMPLATE), str(self.env_file)],
            input=input, capture_output=True, text=True,
        )

    def test_blank_required_input_does_not_assign(self):
        for helper in ("ask", "ask_secret"):
            with self.subTest(helper=helper):
                result = self.ask(helper, input="\n")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("nonempty value is required", result.stderr)
                self.assertNotIn("captured=", result.stdout)
                self.assertFalse(self.env_file.exists())

    def test_enter_preserves_existing_nonempty_value(self):
        self.env_file.write_text("DUMMY='saved-dummy'\n")
        for helper in ("ask", "ask_secret"):
            with self.subTest(helper=helper):
                result = self.ask(helper, input="\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("captured=<saved-dummy>", result.stdout)
                self.assertEqual(self.env_file.read_text(), "DUMMY='saved-dummy'\n")

    def test_optional_empty_input_is_explicitly_allowed(self):
        result = self.ask(input="\n", optional=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("captured=<>", result.stdout)

    def test_eof_and_partial_eof_do_not_assign_even_with_existing_value(self):
        self.env_file.write_text("DUMMY='saved-dummy'\n")
        for helper in ("ask", "ask_secret"):
            for input in ("", "partial-dummy"):
                with self.subTest(helper=helper, input=input):
                    result = self.ask(helper, input=input)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertNotIn("captured=", result.stdout)
                    self.assertEqual(self.env_file.read_text(), "DUMMY='saved-dummy'\n")

    def test_validator_rejection_does_not_leak_value(self):
        result = self.ask(input="dummy-sensitive\n", before='only_ok() { printf "%s" "$1"; [[ "$1" == ok ]]; }',
                          validator="only_ok")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("dummy-sensitive", result.stdout + result.stderr)
        self.assertIn("did not pass validation", result.stderr)

    def test_validator_accepts_valid_value(self):
        result = self.ask(input="ok\n", before='only_ok() { [[ "$1" == ok ]]; }', validator="only_ok")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("captured=<ok>", result.stdout)


if __name__ == "__main__":
    unittest.main()
