import unittest
from src.cli import build_parser


class CliTests(unittest.TestCase):
    def test_json_format_accepted(self):
        args = build_parser().parse_args(["--format", "json"])
        self.assertEqual(args.format, "json")
