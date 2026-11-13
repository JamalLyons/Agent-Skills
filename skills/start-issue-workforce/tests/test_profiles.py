"""Local profiles and arbitrary host rosters; no provider calls or account reads."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile_route', ROOT / 'scripts/route.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.config = self.folder / 'roster.json'
        self.profile = self.folder / 'profile.json'
        cfg = copy.deepcopy(r.load_config())
        cfg['tiers'] = {
            'easy': [{'provider': 'local-engine', 'model': 'small', 'options': {}}],
            'hard': [{'provider': 'other-engine', 'model': 'deep', 'options': {'effort': 'high'}}],
        }
        self.config.write_text(json.dumps(cfg))

    def save(self, **values):
        self.profile.write_text(json.dumps({'version': 1, 'config': 'roster.json', **values}))

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts/route.py'), '--json', *args],
                              cwd=self.folder, capture_output=True, text=True)

    def test_custom_roster_accepts_unrelated_provider_and_model_ids(self):
        result = self.cli('--config', str(self.config), '--steps', 'easy,hard')
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual([x['provider'] for x in data['assignments']], ['local-engine', 'other-engine'])
        self.assertEqual(data['assignments'][1]['options'], {'effort': 'high'})
        self.assertTrue(all(x['source'] == 'unknown' for x in data['usage'].values()))

    def test_profile_roster_is_relative_to_profile_not_launch_directory(self):
        self.save(allow_models=['local-engine/small'], workflow_preferences={
            'max_concurrency': 2, 'review_budget': 1, 'publication': 'propose-pr'})
        result = self.cli('--profile', str(self.profile), '--steps', 'easy,hard')
        data = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(data['assignments'][0]['model'], 'small')
        self.assertIsNone(data['assignments'][1]['model'])
        self.assertEqual(data['workflow_preferences']['publication'], 'propose-pr')
        self.assertIn('authorization', data['advisory'])

    def test_explicit_model_allowlist_replaces_saved_allowlist(self):
        self.save(allow_models=['local-engine/small'])
        result = self.cli('--profile', str(self.profile), '--steps', 'hard',
                          '--allow-model', 'other-engine/deep')
        self.assertEqual(json.loads(result.stdout)['assignments'][0]['model'], 'deep')

    def test_explicit_exclusions_replace_profile_and_saved_exclusions_apply_by_default(self):
        self.save(exclude=['other-engine'])
        blocked = self.cli('--profile', str(self.profile), '--steps', 'hard')
        self.assertIsNone(json.loads(blocked.stdout)['assignments'][0]['model'])
        selected = self.cli('--profile', str(self.profile), '--steps', 'hard', '--exclude', 'local-engine')
        self.assertEqual(json.loads(selected.stdout)['assignments'][0]['model'], 'deep')
        selected = self.cli('--profile', str(self.profile), '--steps', 'hard', '--ignore-profile-routing')
        self.assertEqual(json.loads(selected.stdout)['assignments'][0]['model'], 'deep')

    def test_empty_saved_allowlist_blocks_every_model(self):
        self.save(allow_models=[])
        result = self.cli('--profile', str(self.profile), '--steps', 'easy,hard')
        self.assertTrue(all(x['model'] is None for x in json.loads(result.stdout)['assignments']))

    def test_invalid_profile_and_unavailable_saved_ids_fail_cleanly(self):
        for values in ({'version': True}, {'allow_models': 'all'}, {'unknown': 1},
                       {'workflow_preferences': {'publication': 'authorized'}},
                       {'workflow_preferences': {'max_concurrency': False}},
                       {'allow_models': ['missing/model']}):
            with self.subTest(values=values):
                self.save(**values)
                result = self.cli('--profile', str(self.profile), '--steps', 'hard')
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('Traceback', result.stderr)

    def test_cache_reads_can_be_disabled_and_skip_unrelated_providers(self):
        with patch.object(r, 'claude_usage', side_effect=AssertionError('unexpected read')), \
             patch.object(r, 'codex_usage', side_effect=AssertionError('unexpected read')):
            r.snapshot(r.load_config(), {}, read_caches=False)
            r.snapshot(r.load_config(self.config), {})

    def test_cli_never_writes_profile_or_shared_config(self):
        self.save()
        before = {p: p.read_bytes() for p in (self.profile, self.config, ROOT / 'config.json')}
        result = self.cli('--profile', str(self.profile), '--steps', 'hard', '--set', 'other-engine=80')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == '__main__':
    unittest.main()
