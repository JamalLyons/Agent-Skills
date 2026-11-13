"""Exercise dotenv helpers without opening browsers, using only dummy values."""
import json
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest


TEMPLATE = Path(__file__).resolve().parents[1] / "template.sh"
SUPPORTED = [
    "", "plain-token", "it's-a-token", 'has "double quotes"',
    "  padded value  ", "$USER ${OTHER} # literal", "café-東京",
    r"C:\dummy\path", r"literal\nnot-a-newline", "it's $USER # literal",
]
UNSUPPORTED = ["line one\nline two", "carriage\rreturn", '''both ' and " quotes''',
               "it's\\a-token", "it's\\na-token"]


class DotenvTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_path = Path(self.tmp.name) / ".env"

    def helper(self, action, value="", key="TOKEN"):
        return subprocess.run(
            ["bash", "-c", 'source "$1"; ENV_FILE="$2"; ' + action,
             "test-dotenv", str(TEMPLATE), str(self.env_path), value, key],
            capture_output=True, text=True,
        )

    def write(self, value, key="TOKEN"):
        return self.helper('write_env "$4" "$3" >/dev/null', value, key)

    def test_source_does_not_run_example(self):
        result = subprocess.run(["bash", "-c", 'source "$1"', "source-test", str(TEMPLATE)],
                                capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertFalse(self.env_path.exists())

    def test_existing_round_trip_for_supported_values(self):
        for value in SUPPORTED:
            with self.subTest(value=value):
                self.assertEqual(self.write(value).returncode, 0)
                decoded = self.helper('_existing TOKEN')
                self.assertEqual(decoded.returncode, 0, decoded.stderr)
                self.assertEqual(decoded.stdout, value)

    @unittest.skipUnless(shutil.which("node"), "Node is optional; needed for independent consumer check")
    def test_node_dotenv_consumer_preserves_supported_values(self):
        available = subprocess.run(["node", "-e", 'process.exit(typeof require("node:util").parseEnv === "function" ? 0 : 1)'],
                                   capture_output=True, text=True)
        if available.returncode:
            self.skipTest("installed Node does not expose util.parseEnv")
        for value in SUPPORTED:
            with self.subTest(value=value):
                written = self.write(value)
                self.assertEqual(written.returncode, 0, written.stderr)
                parsed = subprocess.run(
                    ["node", "-e", 'const fs=require("node:fs"); const {parseEnv}=require("node:util"); process.stdout.write(JSON.stringify(parseEnv(fs.readFileSync(process.argv[1], "utf8"))));',
                     str(self.env_path)], capture_output=True, text=True, check=True,
                )
                self.assertEqual(json.loads(parsed.stdout)["TOKEN"], value)

    def test_unsupported_value_leaves_existing_file_unchanged(self):
        original = "# preserve this\nTOKEN='previous'\nOTHER='keep'\n"
        self.env_path.write_text(original)
        self.env_path.chmod(0o640)
        for value in UNSUPPORTED:
            with self.subTest(value=value):
                result = self.write(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("project serializer", result.stderr)
                self.assertNotIn(value, result.stderr)
                self.assertEqual(self.env_path.read_text(), original)
                self.assertEqual(stat.S_IMODE(self.env_path.stat().st_mode), 0o640)

    def test_unsupported_value_does_not_create_file(self):
        result = self.write("has\nnewline")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.env_path.exists())

    def test_upsert_preserves_other_values_and_replaces_duplicates(self):
        self.env_path.write_text("# comment\nOTHER='keep'\nTOKEN='old'\nTOKEN='older'\n")
        result = self.write("it's-new")
        self.assertEqual(result.returncode, 0, result.stderr)
        content = self.env_path.read_text()
        self.assertIn("# comment\nOTHER='keep'\n", content)
        self.assertEqual(sum(line.startswith("TOKEN=") for line in content.splitlines()), 1)
        self.assertEqual(self.helper('_existing TOKEN').stdout, "it's-new")

    def test_invalid_key_does_not_modify_file(self):
        self.env_path.write_text("TOKEN='keep'\n")
        for key in ["", "BAD-KEY", "A.*", "A\nB"]:
            with self.subTest(key=key):
                self.assertNotEqual(self.write("dummy", key).returncode, 0)
                self.assertEqual(self.env_path.read_text(), "TOKEN='keep'\n")

    def test_ambiguous_existing_values_are_not_guessed(self):
        for line in ["TOKEN='it'\\''s-a-token'", 'TOKEN="escape\\nsequence"',
                     "TOKEN='unclosed", 'TOKEN="unclosed', "TOKEN=value # comment"]:
            with self.subTest(line=line):
                self.env_path.write_text(line + "\n")
                result = self.helper('_existing TOKEN')
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
