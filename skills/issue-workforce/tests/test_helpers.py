import contextlib
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('route', ROOT/'scripts/route.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.cfg = r.load_config()
        self.snap = {p: {'weekly_left': 80, 'session_left': 80} for p in
                     ('claudeAgent', 'codex', 'cursor', 'antigravity')}

    def test_default_tiers(self):
        plan, _ = r.allocate(self.cfg, self.snap, ['easy', 'hard'])
        for x in plan:
            self.assertIn(x['model'], [m['model'] for m in self.cfg['tiers'][x['tier']]])

    def test_no_hard_downgrade(self):
        for p in ('claudeAgent', 'codex', 'cursor'):
            self.snap[p]['weekly_left'] = 0
        self.assertIsNone(r.allocate(self.cfg, self.snap, ['hard'])[0][0]['model'])

    def test_reserve_after_allocation(self):
        self.snap = {p: {'weekly_left': 31 if p=='claudeAgent' else 0, 'session_left': 80} for p in self.snap}
        plan, _ = r.allocate(self.cfg, self.snap, ['hard']*3)
        self.assertEqual([bool(x['model']) for x in plan], [True, True, False])

    def test_session_budget_decrements(self):
        self.snap = {p: {'weekly_left': 100 if p=='claudeAgent' else 0, 'session_left': 26} for p in self.snap}
        plan, _ = r.allocate(self.cfg, self.snap, ['hard']*3)
        self.assertEqual([bool(x['model']) for x in plan], [True, True, False])

    def test_weekly_override_keeps_session(self):
        with patch.object(r, 'claude_usage', return_value={'weekly_left':60,'session_left':0}), patch.object(r, 'codex_usage', return_value=None):
            s = r.snapshot(self.cfg, {'claudeAgent':80}, now=1000)
        self.assertEqual(s['claudeAgent']['session_left'], 0)
        self.assertNotEqual(r.allocate(self.cfg, s, ['hard'])[0][0].get('provider'), 'claudeAgent')

    def test_expired_reset_unknown(self):
        self.assertIsNone(r.observation(90, 900, 990, 1000))

    def test_stale_unknown(self):
        self.assertIsNone(r.observation(1, 9000, 100, 5000))

    def test_future_observation_unknown(self):
        self.assertIsNone(r.observation(1, 9000, 1100, 1000))

    def test_exclusion_absolute(self):
        plan, _ = r.allocate(self.cfg, self.snap, ['hard']*20, exclude={'claudeAgent','cursor','codex'})
        self.assertTrue(all(x['model'] is None for x in plan))

    def test_soft_avoid_last_resort(self):
        self.snap['claudeAgent']['weekly_left'] = 100
        self.snap['codex']['weekly_left'] = 23
        self.snap['cursor']['weekly_left'] = 0
        first = r.allocate(self.cfg,self.snap,['hard'],avoid={'claudeAgent'})[0][0]
        self.assertEqual(first['provider'],'codex')
        self.snap['codex']['weekly_left'] = 0
        self.assertEqual(r.allocate(self.cfg,self.snap,['hard'],avoid={'claudeAgent'})[0][0]['provider'],'claudeAgent')

    def test_allowlist(self):
        plan, _ = r.allocate(self.cfg,self.snap,['easy','hard'],allowed={'codex/gpt-6-luna'})
        self.assertEqual(plan[0]['model'], 'gpt-6-luna')
        self.assertIsNone(plan[1]['model'])

    def test_shared_quota(self):
        self.snap = {p: {'weekly_left': 26 if p=='cursor' else 0, 'session_left':80} for p in self.snap}
        plan, _ = r.allocate(self.cfg,self.snap,['easy','hard','easy'])
        self.assertEqual([bool(x['model']) for x in plan], [True, True, False])

    def test_bad_percent(self):
        for x in ('nan', 'inf', -1, 101, True):
            with self.subTest(x=x), self.assertRaises(ValueError):
                r.percent(x)

    def test_unknown_tier(self):
        with self.assertRaisesRegex(ValueError, 'easy or hard'):
            r.allocate(self.cfg,self.snap,['medium'])

    def test_codex_uses_event_not_mtime(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path, 'home', return_value=Path(d)):
            folder=Path(d)/'.codex/sessions';folder.mkdir(parents=True)
            def event(ts, used):
                return {'timestamp':ts,'type':'event_msg','payload':{'type':'token_count','rate_limits':{'primary':{'window_minutes':300,'used_percent':used,'resets_at':6000}}}}
            (folder/'a.jsonl').write_text(json.dumps(event(4500,30))+'\n')
            (folder/'b.jsonl').write_text(json.dumps(event(4000,90))+'\n')
            os.utime(folder/'b.jsonl',(6000,6000))
            self.assertEqual(r.codex_usage(5000)['session_left'],70)

    def test_unknown_window_not_mislabeled(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path,'home',return_value=Path(d)):
            f=Path(d)/'.codex/sessions';f.mkdir(parents=True)
            (f/'a.jsonl').write_text(json.dumps({'timestamp':4500,'type':'event_msg','payload':{'type':'token_count','rate_limits':{'primary':{'window_minutes':60,'used_percent':5}}}})+'\n')
            self.assertIsNone(r.codex_usage(5000)['session_left'])

    def test_cli_invalid_input_clean_error(self):
        for args in (['--steps','easy,,hard'], ['--set','gpt=nan'], ['--exclude','made-up'], ['--steps','unknown']):
            with self.subTest(args=args), patch('sys.argv',['route.py']+args), patch.object(r,'snapshot',return_value=self.snap), contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as ex:r.main()
                self.assertEqual(ex.exception.code,2)
                self.assertNotIn('Traceback',err.getvalue())

    def test_malformed_cache_unknown(self):
        with tempfile.TemporaryDirectory() as d, patch.object(Path,'home',return_value=Path(d)):
            (Path(d)/'.claude.json').write_text('{broken')
            self.assertIsNone(r.claude_usage(5000))


class DetectionTests(unittest.TestCase):
    def detect(self, files, no_tools=False):
        with tempfile.TemporaryDirectory() as d:
            for name, content in files.items(): (Path(d)/name).write_text(content)
            env=dict(os.environ)
            if no_tools:
                bindir=Path(d)/'bin';bindir.mkdir()
                for cmd in ('grep','tr','ls'):
                    import shutil
                    (bindir/cmd).symlink_to(shutil.which(cmd))
                env['PATH']=str(bindir)
            return subprocess.run(['/bin/bash',str(ROOT/'scripts/detect_checks.sh')],cwd=d,env=env,text=True,capture_output=True,check=True).stdout

    def test_just_without_installed_just(self):
        out=self.detect({'justfile':'test:\n    echo ok\n'},no_tools=True)
        self.assertIn('just test',out)

    def test_no_candidates_message(self):
        self.assertIn('No candidate checks',self.detect({'Makefile':'deploy:\n\techo nope\n'}))

    def test_malformed_package_message(self):
        self.assertIn('No candidate checks',self.detect({'package.json':'{broken'}))

    def test_cargo_check_hints(self):
        self.assertIn('cargo fmt --check',self.detect({'Cargo.toml':''}))

if __name__=='__main__': unittest.main(verbosity=2)
