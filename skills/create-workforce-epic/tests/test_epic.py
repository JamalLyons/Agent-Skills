"""Deterministic tests for create-workforce-epic helpers. No network: GitHub is simulated."""
import copy
import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import apply_plan  # noqa: E402
import epic_status  # noqa: E402
from epiclib import (Gh, GhError, PlanError, parse_epic_marker, parse_include,  # noqa: E402
                     parse_marker, paths_overlap, render_body, render_epic_body, validate_plan)

REPO = 'acme/app'


def base_plan(**over):
    plan = {
        'version': 1, 'repo': REPO, 'epic': 1,
        'criteria': [
            {'id': 'C1', 'text': 'API exists', 'covered_by': ['T1']},
            {'id': 'C2', 'text': 'UI uses API', 'covered_by': ['T2', 'T3']},
            {'id': 'C3', 'text': 'Docs site', 'deferred': 'separate epic'},
        ],
        'tasks': [
            {'key': 'T1', 'title': 'Add API', 'tier': 'hard', 'summary': 'Build the API.',
             'owned_paths': ['src/api/'], 'acceptance': ['GET /x returns 200'], 'verify': ['make test']},
            {'key': 'T2', 'title': 'Wire UI', 'tier': 'easy', 'summary': 'Use the API.',
             'owned_paths': ['src/ui/'], 'acceptance': ['Page shows x'], 'verify': ['make test'],
             'blocked_by': ['T1']},
            {'key': 'T3', 'title': 'Sign release', 'kind': 'human', 'summary': 'Needs certs.',
             'acceptance': ['Signed build exists'], 'blocked_by': ['T2', '#9']},
        ],
    }
    plan.update(over)
    return plan


def new_epic_plan(**epic_over):
    epic = {'key': 'csv-export', 'title': 'CSV export', 'summary': 'Let users export reports.',
            'background': 'Customers ask for spreadsheets.', 'out_of_scope': ['PDF']}
    epic.update(epic_over)
    return base_plan(epic=epic)


class FakeGitHub(Gh):
    """In-memory GitHub covering the REST calls apply_plan makes."""

    def __init__(self, deps_supported=True):
        super().__init__(runner=lambda *a: None)
        self.issues = {}          # number -> issue dict
        self.subs = {}            # parent number -> [child ids]
        self.parent = {}          # child id -> parent number
        self.blocked_by = {}      # number -> [blocker ids]
        self.labels = set()
        self.writes = []
        self.deps_supported = deps_supported
        self.fail_on = None       # (method, path regex, nth occurrence)
        self.next_number = 1
        self.add_issue('Epic', 'epic body')
        self.add_issue('Prior work', 'old', state='closed')   # #2
        self.next_number = 9
        self.add_issue('External blocker', 'ext')             # #9

    def add_issue(self, title, body, labels=(), state='open', pr=False):
        n = self.next_number
        self.next_number += 1
        issue = {'number': n, 'id': 1000 + n, 'title': title, 'body': body, 'state': state,
                 'labels': [{'name': x} for x in labels]}
        if pr:
            issue['pull_request'] = {}
        self.issues[n] = issue
        return issue

    def _by_id(self, i):
        return next(x for x in self.issues.values() if x['id'] == i)

    def rest(self, method, path, body=None):
        fail = None
        if method != 'GET':
            self.writes.append((method, path, body))
            if self.fail_on and method == self.fail_on[0] and re.search(self.fail_on[1], path):
                m, rx, nth, when = self.fail_on
                self.fail_on = (m, rx, nth - 1, when)
                if nth == 1:
                    self.fail_on, fail = None, when
        if fail == 'before':
            raise GhError(None, 'connection reset')
        result = self._dispatch(method, path, body)
        if fail == 'after':                      # server applied the write, client lost the reply
            raise GhError(None, 'timed out')
        return result

    def _dispatch(self, method, path, body):
        path, _, query = path.partition('?')
        parts = path.split('/')[3:]          # after repos/acme/app
        q = dict(p.split('=', 1) for p in query.split('&') if p)
        page = int(q.get('page', 1))
        if parts[0] == 'labels':
            if method == 'GET':
                if parts[1] in self.labels:
                    return {'name': parts[1]}
                raise GhError(404, 'Not Found')
            self.labels.add(body['name'])
            return {'name': body['name']}
        if parts == ['issues']:
            if method == 'POST':
                assert all(lbl in self.labels for lbl in body['labels']), 'label must exist first'
                return copy.deepcopy(self.add_issue(body['title'], body['body'], body['labels']))
            want = q['labels']
            items = [i for i in self.issues.values() if any(lb['name'] == want for lb in i['labels'])]
            return copy.deepcopy(items[(page - 1) * 100: page * 100])
        n = int(parts[1])
        if n not in self.issues:
            raise GhError(404, 'Not Found')
        rest = parts[2:]
        if not rest:
            return copy.deepcopy(self.issues[n])
        if rest == ['sub_issues']:
            if method == 'GET':
                return [copy.deepcopy(self._by_id(i)) for i in self.subs.get(n, [])][(page - 1) * 100: page * 100]
            cid = body['sub_issue_id']
            if cid in self.parent:
                raise GhError(422, 'Validation Failed')
            self.subs.setdefault(n, []).append(cid)
            self.parent[cid] = n
            return copy.deepcopy(self.issues[n])
        if rest == ['parent']:
            pid = self.parent.get(self.issues[n]['id'])
            if pid is None:
                raise GhError(404, 'Not Found')
            return copy.deepcopy(self.issues[pid])
        if rest == ['dependencies', 'blocked_by']:
            if not self.deps_supported:
                raise GhError(404, 'Not Found')
            if method == 'GET':
                return [copy.deepcopy(self._by_id(i)) for i in self.blocked_by.get(n, [])]
            self.blocked_by.setdefault(n, []).append(body['issue_id'])
            return copy.deepcopy(self._by_id(body['issue_id']))
        raise AssertionError(f'unexpected call {method} {path}')


def write_plan(d, plan):
    p = Path(d) / 'plan.json'
    p.write_text(json.dumps(plan))
    return str(p)


def run_apply(gh, plan, *extra):
    with tempfile.TemporaryDirectory() as d:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = apply_plan.main(['apply', write_plan(d, plan), '--delay', '0', '--json', *extra], gh=gh)
        report = json.loads(out.getvalue()) if out.getvalue().strip() else None
        return code, report, err.getvalue()


class ValidationTests(unittest.TestCase):
    def errors(self, plan):
        with self.assertRaises(PlanError) as cm:
            validate_plan(plan)
        return '\n'.join(cm.exception.errors)

    def test_valid_plan_orders_dependencies_first(self):
        plan = validate_plan(base_plan())
        self.assertEqual(plan.order, ['T1', 'T2', 'T3'])
        self.assertEqual(plan.label, 'workforce')

    def test_documented_example_is_valid(self):
        data = json.loads((ROOT / 'references' / 'plan.example.json').read_text())
        plan = validate_plan(data)
        self.assertEqual(plan.order, ['T1', 'H1', 'T2', 'T3'])
        self.assertEqual(plan.warnings, [])

    def test_new_epic_example_is_valid(self):
        data = json.loads((ROOT / 'references' / 'plan.new-epic.example.json').read_text())
        plan = validate_plan(data)
        self.assertEqual((plan.epic, plan.epic_spec['key'], plan.warnings), (None, 'csv-export', []))

    def test_cycle_detected(self):
        p = base_plan()
        p['tasks'][0]['blocked_by'] = ['T2']
        self.assertIn('dependency cycle', self.errors(p))

    def test_unknown_and_self_blockers(self):
        p = base_plan()
        p['tasks'][0]['blocked_by'] = ['T9', 'T1', '#1']
        e = self.errors(p)
        self.assertIn('unknown blocker "T9"', e)
        self.assertIn('blocked by itself', e)
        self.assertIn('own epic #1', e)

    def test_duplicate_keys_and_bad_tier(self):
        p = base_plan()
        p['tasks'][1]['key'] = 'T1'
        p['tasks'][0]['tier'] = 'medium'
        e = self.errors(p)
        self.assertIn('duplicate key', e)
        self.assertIn('tier', e)

    def test_human_task_rules(self):
        p = base_plan()
        p['tasks'][2]['tier'] = 'easy'
        self.assertIn('human tasks must not set "tier"', self.errors(p))

    def test_agent_needs_acceptance_and_verify(self):
        p = base_plan()
        p['tasks'][0]['acceptance'] = []
        p['tasks'][0]['verify'] = []
        e = self.errors(p)
        self.assertIn('acceptance criterion', e)
        self.assertIn('verification command', e)

    def test_criteria_coverage(self):
        p = base_plan()
        p['criteria'][0] = {'id': 'C1', 'text': 'x'}
        p['criteria'][1]['covered_by'] = ['T7']
        p['criteria'][2]['covered_by'] = ['T1']
        e = self.errors(p)
        self.assertIn('criterion C1: set exactly one', e)
        self.assertIn('unknown task "T7"', e)
        self.assertIn('criterion C3: set exactly one', e)
        self.assertIn('"criteria" must list', self.errors(base_plan(criteria=[])))

    def test_reserved_marker_rejected(self):
        p = base_plan()
        p['tasks'][0]['notes'] = '<!-- workforce-epic: {} -->'
        self.assertIn('reserved marker', self.errors(p))

    def test_task_limit(self):
        p = base_plan()
        self.assertIn('exceeds the limit', '\n'.join(self._limit(p)))

    def _limit(self, p):
        with self.assertRaises(PlanError) as cm:
            validate_plan(p, max_tasks=2)
        return cm.exception.errors

    def test_warnings_for_uncovered_and_parallel_overlap(self):
        p = base_plan()
        p['tasks'].append({'key': 'T4', 'title': 'Refactor API', 'tier': 'easy', 'summary': 's',
                           'owned_paths': ['src/api/routes.ts'], 'acceptance': ['a'], 'verify': ['v']})
        w = '\n'.join(validate_plan(p).warnings)
        self.assertIn('T4: covers no epic criterion', w)
        self.assertIn('T1 and T4 are unordered', w)

    def test_ordered_overlap_is_fine(self):
        p = base_plan()
        p['tasks'][1]['owned_paths'] = ['src/api/client.ts']
        self.assertFalse(any('unordered' in w for w in validate_plan(p).warnings))

    def test_paths_overlap(self):
        self.assertTrue(paths_overlap('src/a', 'src/a/b.ts'))
        self.assertTrue(paths_overlap('src/**/x.ts', 'src/y.ts'))
        self.assertFalse(paths_overlap('src/ab', 'src/a'))
        self.assertTrue(paths_overlap('*.md', 'src/a'))


class RenderTests(unittest.TestCase):
    def test_body_has_marker_sections_and_refs(self):
        plan = validate_plan(base_plan())
        body = render_body(plan, plan.by_key['T3'], {'T2': '#5', '#9': '#9'})
        meta = parse_marker(body)
        self.assertEqual(meta, {'v': 1, 'epic': 'acme/app#1', 'key': 'T3', 'kind': 'human'})
        self.assertIn('**needs a human**', body)
        self.assertIn('Blocked by #5, #9', body)
        self.assertIn('**C2**: UI uses API', body)
        self.assertIn('- [ ] Signed build exists', body)

    def test_marker_parse_rejects_garbage(self):
        self.assertIsNone(parse_marker('<!-- workforce-epic: {not json} -->'))
        self.assertIsNone(parse_marker('<!-- workforce-epic: {"key": 3, "epic": "x"} -->'))
        self.assertIsNone(parse_marker(None))


class ApplyTests(unittest.TestCase):
    def test_dry_run_writes_nothing(self):
        gh = FakeGitHub()
        code, rep, _ = run_apply(gh, base_plan())
        self.assertEqual(code, 0)
        self.assertEqual(gh.writes, [])
        kinds = [a['action'] for a in rep['actions']]
        self.assertEqual(kinds.count('create'), 3)
        self.assertIn('label', kinds)
        self.assertTrue(all(a['status'] == 'planned' for a in rep['actions']))

    def test_execute_creates_links_and_dependencies(self):
        gh = FakeGitHub()
        code, rep, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0, err)
        nums = rep['tasks']
        self.assertEqual(sorted(gh.subs[1]), sorted(gh.issues[n]['id'] for n in nums.values()))
        self.assertEqual(gh.blocked_by[nums['T2']], [gh.issues[nums['T1']]['id']])
        self.assertEqual(sorted(gh.blocked_by[nums['T3']]), sorted([gh.issues[nums['T2']]['id'], 1009]))
        body = gh.issues[nums['T3']]['body']
        self.assertIn(f'Blocked by #{nums["T2"]}, #9', body)
        self.assertEqual(parse_marker(body)['key'], 'T3')

    def test_rerun_is_idempotent(self):
        gh = FakeGitHub()
        run_apply(gh, base_plan(), '--execute')
        before = len(gh.writes)
        code, rep, _ = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0)
        self.assertEqual(len(gh.writes), before)
        self.assertEqual({a['action'] for a in rep['actions']}, {'reuse'})

    def test_resume_after_ambiguous_create_failure(self):
        gh = FakeGitHub()
        gh.fail_on = ('POST', r'/issues/\d+/sub_issues$', 2, 'before')   # second link attempt fails
        code, _, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 1)
        self.assertIn('Re-run', err)
        code, rep, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0, err)
        titles = [i['title'] for i in gh.issues.values()]
        self.assertEqual(titles.count('Wire UI'), 1)
        self.assertEqual(len(gh.subs[1]), 3)

    def test_resume_after_lost_create_response(self):
        gh = FakeGitHub()
        gh.fail_on = ('POST', r'/issues$', 2, 'after')   # T2 is created but the reply is lost
        code, _, _ = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 1)
        code, rep, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0, err)
        titles = [i['title'] for i in gh.issues.values()]
        self.assertEqual((titles.count('Wire UI'), titles.count('Sign release')), (1, 1))
        t2 = rep['tasks']['T2']
        self.assertEqual(gh.blocked_by[t2], [gh.issues[rep['tasks']['T1']]['id']])
        self.assertEqual(len(gh.subs[1]), 3)

    def test_unlinked_issue_found_by_label(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        plan = validate_plan(base_plan())
        gh.add_issue('Add API', render_body(plan, plan.by_key['T1'], {}), labels=['workforce'])
        code, rep, _ = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0)
        self.assertEqual([i['title'] for i in gh.issues.values()].count('Add API'), 1)
        self.assertIn('sub-issue', [a['action'] for a in rep['actions'] if a['task'] == 'T1'])

    def test_duplicate_markers_stop(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        plan = validate_plan(base_plan())
        for _ in range(2):
            gh.add_issue('Add API', render_body(plan, plan.by_key['T1'], {}), labels=['workforce'])
        code, _, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('several issues', err)

    def test_other_parent_is_not_replaced(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        plan = validate_plan(base_plan())
        other = gh.add_issue('Other epic', '')
        t1 = gh.add_issue('Add API', render_body(plan, plan.by_key['T1'], {}), labels=['workforce'])
        gh.subs[other['number']] = [t1['id']]
        gh.parent[t1['id']] = other['number']
        code, _, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('not moving it', err)
        self.assertFalse(any('replace_parent' in (w[2] or {}) for w in gh.writes))

    def test_missing_external_blocker_stops_before_writes(self):
        p = base_plan()
        p['tasks'][2]['blocked_by'] = ['#77']
        gh = FakeGitHub()
        code, _, err = run_apply(gh, p, '--execute')
        self.assertEqual(code, 2)
        self.assertIn('#77 does not exist', err)
        self.assertEqual(gh.writes, [])

    def test_epic_must_be_open_issue(self):
        gh = FakeGitHub()
        gh.issues[1]['state'] = 'closed'
        code, _, err = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('closed', err)
        gh = FakeGitHub()
        gh.issues[1]['pull_request'] = {}
        self.assertIn('pull request', run_apply(gh, base_plan())[2])

    def test_dependencies_unavailable_degrades(self):
        gh = FakeGitHub(deps_supported=False)
        code, rep, _ = run_apply(gh, base_plan(), '--execute')
        self.assertEqual(code, 0)
        self.assertTrue(any('dependencies API unavailable' in w for w in rep['warnings']))
        self.assertEqual(len(gh.subs[1]), 3)

    def test_invalid_plan_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            err = io.StringIO()
            with redirect_stderr(err):
                code = apply_plan.main(['validate', write_plan(d, {'version': 2})])
        self.assertEqual(code, 2)
        self.assertIn('plan invalid', err.getvalue())


class NewEpicTests(unittest.TestCase):
    def test_validation(self):
        plan = validate_plan(new_epic_plan())
        self.assertIsNone(plan.epic)
        self.assertEqual(plan.epic_ref, 'acme/app#new')
        with self.assertRaises(PlanError) as cm:
            validate_plan(new_epic_plan(key='bad key', title='', summary='', notes='workforce-epic'))
        e = '\n'.join(cm.exception.errors)
        for needle in ('epic: "key"', 'epic: "title"', 'epic: "summary"', 'reserved marker'):
            self.assertIn(needle, e)
        with self.assertRaises(PlanError) as cm:
            validate_plan(base_plan(epic='42'))
        self.assertIn('object describing a new epic', cm.exception.errors[0])

    def test_epic_body(self):
        plan = validate_plan(new_epic_plan())
        body = render_epic_body(plan)
        self.assertEqual(parse_epic_marker(body), {'v': 1, 'key': 'csv-export'})
        self.assertIsNone(parse_marker(body))          # not mistaken for a task
        self.assertIn('- [ ] **C1**: API exists', body)
        self.assertIn('**C3** (deferred): Docs site. separate epic', body)
        self.assertIn('## Out of scope\n- PDF', body)
        self.assertIn('Part of the new epic', render_body(plan, plan.by_key['T1'], {}))

    def test_dry_run_plans_epic_first_and_writes_nothing(self):
        gh = FakeGitHub()
        code, rep, _ = run_apply(gh, new_epic_plan())
        self.assertEqual(code, 0)
        self.assertEqual(gh.writes, [])
        self.assertEqual([a['action'] for a in rep['actions']][:3], ['label', 'epic', 'create'])
        self.assertIn('new epic "CSV export"', rep['actions'][3]['detail'])
        self.assertIsNone(rep['epic'])

    def test_execute_creates_epic_then_tasks(self):
        gh = FakeGitHub()
        code, rep, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 0, err)
        self.assertTrue(rep['epic_created'])
        epic = gh.issues[rep['epic']]
        self.assertEqual(epic['title'], 'CSV export')
        self.assertEqual([lb['name'] for lb in epic['labels']], ['workforce'])
        self.assertEqual(len(gh.subs[rep['epic']]), 3)
        t1 = gh.issues[rep['tasks']['T1']]
        self.assertEqual(parse_marker(t1['body'])['epic'], f'acme/app#{rep["epic"]}')
        self.assertIn(f'Part of #{rep["epic"]}', t1['body'])
        self.assertEqual(gh.writes[1][1], 'repos/acme/app/issues')     # epic right after the label
        self.assertEqual(gh.writes[1][2]['title'], 'CSV export')

    def test_rerun_reuses_epic(self):
        gh = FakeGitHub()
        first = run_apply(gh, new_epic_plan(), '--execute')[1]
        before = len(gh.writes)
        code, rep, _ = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 0)
        self.assertEqual(len(gh.writes), before)
        self.assertEqual(rep['epic'], first['epic'])
        self.assertFalse(rep['epic_created'])

    def test_lost_epic_response_does_not_duplicate(self):
        gh = FakeGitHub()
        gh.fail_on = ('POST', r'/issues$', 1, 'after')
        self.assertEqual(run_apply(gh, new_epic_plan(), '--execute')[0], 1)
        code, rep, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 0, err)
        titles = [i['title'] for i in gh.issues.values()]
        self.assertEqual(titles.count('CSV export'), 1)
        self.assertEqual(len(gh.subs[rep['epic']]), 3)

    def test_duplicate_or_closed_epic_stops(self):
        gh = FakeGitHub()
        gh.labels.add('workforce')
        body = render_epic_body(validate_plan(new_epic_plan()))
        gh.add_issue('CSV export', body, labels=['workforce'])
        gh.add_issue('CSV export', body, labels=['workforce'])
        code, _, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('several issues', err)
        gh = FakeGitHub()
        gh.labels.add('workforce')
        gh.add_issue('CSV export', body, labels=['workforce'], state='closed')
        code, _, err = run_apply(gh, new_epic_plan(), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('closed', err)
        self.assertEqual(gh.writes, [])

    def test_different_key_creates_separate_epic(self):
        gh = FakeGitHub()
        run_apply(gh, new_epic_plan(), '--execute')
        rep = run_apply(gh, new_epic_plan(key='csv-export-2'), '--execute')[1]
        self.assertTrue(rep['epic_created'])

    def test_render_includes_epic_offline(self):
        with tempfile.TemporaryDirectory() as d:
            out = io.StringIO()
            with redirect_stdout(out):
                code = apply_plan.main(['render', write_plan(d, new_epic_plan()), '--json'])
        self.assertEqual(code, 0)
        data = json.loads(out.getvalue())
        self.assertEqual(list(data)[:2], ['epic', 'T1'])
        self.assertIn('workforce-epic-root', data['epic']['body'])

    def test_missing_numbered_epic_is_plan_error(self):
        code, _, err = run_apply(FakeGitHub(), base_plan(epic=500), '--execute')
        self.assertEqual(code, 2)
        self.assertIn('does not exist', err)


class GhClientTests(unittest.TestCase):
    def test_parse_include(self):
        out = 'HTTP/2.0 404 Not Found\r\nX-A: b\r\n\r\n{"message":"Not Found"}'
        self.assertEqual(parse_include(out), (404, {'message': 'Not Found'}))
        self.assertEqual(parse_include('HTTP/2.0 204 No Content\n\n'), (204, None))
        self.assertEqual(parse_include('garbage'), (None, None))

    def test_rest_raises_status(self):
        class P:
            stdout = 'HTTP/2.0 422 Unprocessable\n\n{"message":"Validation Failed"}'
            stderr = ''
        gh = Gh(runner=lambda args, stdin: P())
        with self.assertRaises(GhError) as cm:
            gh.rest('POST', 'repos/a/b/issues', {'x': 1})
        self.assertEqual(cm.exception.status, 422)

    def test_rest_sends_body_on_stdin(self):
        seen = {}

        class P:
            stdout = 'HTTP/2.0 201 Created\n\n{"number": 3}'
            stderr = ''

        def runner(args, stdin):
            seen['args'], seen['stdin'] = args, stdin
            return P()
        self.assertEqual(Gh(runner=runner).rest('POST', 'repos/a/b/issues', {'title': 't'}), {'number': 3})
        self.assertIn('--input', seen['args'])
        self.assertEqual(json.loads(seen['stdin']), {'title': 't'})


def node(number, state='OPEN', reason=None, body=None, closer=None, prs=(), blockers=(), repo=REPO):
    return {
        'number': number, 'title': f'Task {number}', 'state': state, 'stateReason': reason,
        'url': f'https://github.com/{repo}/issues/{number}', 'body': body,
        'repository': {'nameWithOwner': repo},
        'assignees': {'nodes': []},
        'closedByPullRequestsReferences': {'nodes': list(prs)},
        'timelineItems': {'nodes': [{'closer': closer}] if closer else []},
        'blockedBy': {'pageInfo': {'hasNextPage': False}, 'nodes': list(blockers)},
    }


def marker(key, kind='agent', tier='easy'):
    meta = {'v': 1, 'epic': f'{REPO}#1', 'key': key, 'kind': kind}
    if kind == 'agent':
        meta['tier'] = tier
    return f'<!-- workforce-epic: {json.dumps(meta)} -->'


MERGED = {'__typename': 'PullRequest', 'number': 50, 'merged': True}


class StatusTests(unittest.TestCase):
    def status(self, nodes):
        return epic_status.build_status({'number': 1, 'title': 'Epic', 'state': 'OPEN'}, nodes, REPO)

    def by_num(self, st):
        return {t['number']: t for t in st['tasks']}

    def test_classification(self):
        done = node(2, 'CLOSED', 'COMPLETED', marker('T1'), closer=MERGED)
        unverified = node(3, 'CLOSED', 'COMPLETED', marker('T2'))
        dropped = node(4, 'CLOSED', 'NOT_PLANNED', marker('T3'))
        st = self.status([
            done, unverified, dropped,
            node(5, body=marker('T4'), blockers=[done]),
            node(6, body=marker('T5'), blockers=[unverified]),
            node(7, body=marker('T6'), blockers=[dropped]),
            node(8, body=marker('T7'), blockers=[node(5)]),
            node(9, body=marker('T8', 'human')),
            node(10, body=marker('T9'), prs=[{'number': 60, 'state': 'OPEN', 'merged': False}]),
        ])
        s = {n: t['status'] for n, t in self.by_num(st).items()}
        self.assertEqual(s, {2: 'done', 3: 'done-unverified', 4: 'dropped', 5: 'ready', 6: 'check',
                             7: 'blocked', 8: 'blocked', 9: 'human', 10: 'in-review'})
        self.assertIn('re-plan', self.by_num(st)[7]['reason'])
        self.assertEqual(st['ready'], [5])

    def test_commit_closer_and_merged_reference_count_as_evidence(self):
        a = node(2, 'CLOSED', 'COMPLETED', closer={'__typename': 'Commit'})
        b = node(3, 'CLOSED', 'COMPLETED', prs=[{'number': 9, 'state': 'MERGED', 'merged': True}])
        st = self.status([a, b])
        self.assertEqual([t['status'] for t in st['tasks']], ['done', 'done'])

    def test_human_task_closed_without_pr_is_done(self):
        h = node(2, 'CLOSED', 'COMPLETED', marker('T1', 'human'))
        st = self.status([h, node(3, body=marker('T2'), blockers=[h])])
        self.assertEqual(st['ready'], [3])

    def test_dependency_order_and_unmanaged_warning(self):
        st = self.status([node(9, body=marker('T2'), blockers=[node(3)]), node(3, body=marker('T1')), node(5)])
        self.assertEqual([t['number'] for t in st['tasks']], [3, 5, 9])
        self.assertEqual(len([w for w in st['warnings'] if 'not created by' in w]), 1)

    def test_cross_repo_blocker_reference(self):
        ext = node(4, repo='acme/other')
        st = self.status([node(2, body=marker('T1'), blockers=[ext])])
        self.assertIn('acme/other#4', st['tasks'][0]['reason'])
        self.assertEqual(st['tasks'][0]['blocked_by'], [])

    def test_fetch_paginates(self):
        pages = [
            {'repository': {'issue': {'number': 1, 'title': 'E', 'state': 'OPEN', 'url': '',
                                      'subIssues': {'pageInfo': {'hasNextPage': True, 'endCursor': 'c1'},
                                                    'nodes': [node(2)]}}}},
            {'repository': {'issue': {'number': 1, 'title': 'E', 'state': 'OPEN', 'url': '',
                                      'subIssues': {'pageInfo': {'hasNextPage': False, 'endCursor': None},
                                                    'nodes': [node(3)]}}}},
        ]
        calls = []

        class G(Gh):
            def graphql(self, q, v):
                calls.append(v['after'])
                return pages[len(calls) - 1]
        st = epic_status.fetch(G(), REPO, 1)
        self.assertEqual(calls, [None, 'c1'])
        self.assertEqual(len(st['tasks']), 2)

    def test_missing_epic(self):
        class G(Gh):
            def graphql(self, q, v):
                return {'repository': {'issue': None}}
        err = io.StringIO()
        with redirect_stderr(err):
            code = epic_status.main(['--repo', REPO, '--epic', '1'], gh=G())
        self.assertEqual(code, 1)
        self.assertIn('not found', err.getvalue())


if __name__ == '__main__':
    unittest.main(verbosity=2)
