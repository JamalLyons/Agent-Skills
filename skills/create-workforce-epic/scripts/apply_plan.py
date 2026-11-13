#!/usr/bin/env python3
"""Validate, preview, or apply a create-workforce-epic plan.

  apply_plan.py validate plan.json            check the plan offline
  apply_plan.py render plan.json [--task T1]  print issue bodies offline
  apply_plan.py apply plan.json               dry run: read GitHub, print intended writes
  apply_plan.py apply plan.json --execute     perform the writes

Apply is idempotent. Each task issue carries a hidden marker naming the epic and
task key, and existing issues are found through the epic's sub-issues and the
plan label, so re-running resumes after a partial failure without duplicates.
Existing issues are never edited, closed, or moved from another parent.
Exit codes: 0 ok, 1 GitHub/runtime failure, 2 invalid plan or usage.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from epiclib import (EPIC_MARKER_RE, MARKER_RE, EXTERNAL_RE, Gh, GhError, Plan, PlanError, load_plan,  # noqa: E402
                     parse_epic_marker, parse_marker, render_body, render_epic_body)

LABEL_COLOR = '5319e7'
LABEL_DESC = 'Task issue created by create-workforce-epic'
MANAGED_SECTIONS = {'Preamble', 'Summary', 'Background', 'Scope', 'Out of scope',
                    'Owned paths', 'Acceptance criteria', 'Verification',
                    'Epic criteria covered', 'Dependencies', 'Notes', 'Tasks'}


def managed_sections(body: str) -> dict[str, str]:
    """Read sections without treating headings inside code as sections.

    Return custom headings too: plan fields may contain them. The comparison
    determines which extra sections are generated and which are appended notes.
    """
    sections: dict[str, list[str]] = {'Preamble': []}
    current, fence = 'Preamble', None
    body = MARKER_RE.sub('', EPIC_MARKER_RE.sub('', body or ''))
    for line in body.replace('\r\n', '\n').splitlines():
        mark = re.match(r'^\s*(`{3,}|~{3,})', line)
        if mark:
            token = mark.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
        heading = re.match(r'^## (.+?)\s*$', line) if fence is None else None
        if heading:
            current = heading.group(1)
            sections.setdefault(current, [])
        else:
            sections[current].append(line.rstrip())
    result = {}
    for name, lines in sections.items():
        content = '\n'.join(lines).strip()
        if name in {'Acceptance criteria', 'Epic criteria covered'}:
            content = re.sub(r'(?m)^- \[[xX]\] ', '- [ ] ', content)
        if content:
            result[name] = content
    return result


def body_drift(current: str, proposed: str, root: bool = False,
               dependency_aliases: dict[str, str] | None = None) -> dict:
    existing, expected = managed_sections(current), managed_sections(proposed)
    generated_names = MANAGED_SECTIONS | expected.keys()
    # Custom headings in proposed fields are generated content. Interior extra
    # sections in the current body may also be removed generated content; keep
    # them in the comparison. Only trailing, otherwise unknown notes are ignored.
    last_generated = max((i for i, name in enumerate(existing) if name in generated_names), default=-1)
    existing = {name: value for i, (name, value) in enumerate(existing.items())
                if name in generated_names or i < last_generated}
    changes = {}
    parser = parse_epic_marker if root else parse_marker
    if parser(current) != parser(proposed):
        changes['Marker'] = {'current': json.dumps(parser(current), sort_keys=True),
                             'proposed': json.dumps(parser(proposed), sort_keys=True)}
    for section in sorted(existing.keys() | expected.keys()):
        before, after = existing.get(section, ''), expected.get(section, '')
        if section == 'Dependencies' and before.startswith('Blocked by ') and after.startswith('Blocked by '):
            aliases = dependency_aliases or {}
            def refs(value):
                return sorted(aliases.get(x.strip(), x.strip()) for x in value[11:].split(','))
            if refs(before) == refs(after):
                continue
        if before != after:
            changes[section] = {'current': before, 'proposed': after}
    return changes


class Applier:
    def __init__(self, plan: Plan, gh: Gh, execute: bool, delay: float = 1.0, log=print):
        self.plan, self.gh, self.execute, self.delay, self.log = plan, gh, execute, delay, log
        self.base = f'repos/{plan.repo}'
        self.actions: list[dict] = []
        self.warnings: list[str] = list(plan.warnings)
        self.issues: dict[str, dict] = {}      # task key -> {number, id, title, state}
        self.external: dict[str, dict] = {}    # "#n" -> {number, id}
        self.sub_ids: set[int] = set()
        self.deps_supported = True
        self.epic_created = False
        self.existing_epic: dict | None = None
        self.drift: list[dict] = []

    # -- helpers
    def _act(self, kind: str, key: str | None, detail: str, done: bool) -> None:
        self.actions.append({'action': kind, 'task': key, 'detail': detail,
                             'status': 'done' if done else ('planned' if not self.execute else 'pending')})
        tag = 'done ' if done else ('plan ' if not self.execute else '...  ')
        self.log(f'{tag} {kind:<10} {key or "-":<8} {detail}')

    def _write(self, method: str, path: str, body: dict):
        result = self.gh.rest(method, path, body)
        if self.delay:
            time.sleep(self.delay)   # GitHub asks for ~1s between content-creating requests
        return result

    # -- phases
    def preflight(self) -> None:
        labelled = self.gh.paginate(f'{self.base}/issues?state=all&labels={quote(self.plan.label)}')
        if self.plan.epic_spec:
            self.find_new_epic(labelled)
        else:
            try:
                epic = self.gh.rest('GET', f'{self.base}/issues/{self.plan.epic}')
            except GhError as e:
                if e.status == 404:
                    raise PlanError([f'epic #{self.plan.epic} does not exist in {self.plan.repo}; '
                                     'use an "epic" object to create a new one']) from e
                raise
            self.check_epic(epic)
        subs = self.gh.paginate(f'{self.base}/issues/{self.plan.epic}/sub_issues') if self.plan.epic else []
        self.sub_ids = {s['id'] for s in subs}
        self.find_tasks(subs, labelled)
        self.check_external_blockers()
        self.check_scope_drift()

    def check_epic(self, epic: dict) -> None:
        if 'pull_request' in epic:
            raise PlanError([f'#{epic["number"]} is a pull request, not an issue'])
        if epic.get('state') != 'open':
            raise PlanError([f'epic #{epic["number"]} is closed; reopen it or choose another epic'])

    def find_new_epic(self, labelled: list[dict]) -> None:
        """A plan that defines its own epic: reuse the issue carrying its root marker, if any."""
        spec = self.plan.epic_spec
        roots = [i for i in labelled if 'pull_request' not in i
                 and (parse_epic_marker(i.get('body')) or {}).get('key') == spec['key']]
        if len(roots) > 1:
            raise PlanError([f'epic key "{spec["key"]}" already exists as several issues: '
                             + ', '.join(f'#{i["number"]}' for i in roots)
                             + '; closing extras does not resolve marker identity. With explicit authorization, '
                             'choose the canonical epic and rename only the extras\' workforce-epic-root '
                             'markers to workforce-epic-root-superseded; preserve their content. '
                             'See references/github.md, Duplicate-marker recovery, then dry-run again'])
        if roots:
            self.check_epic(roots[0])
            self.existing_epic = roots[0]
            self.plan.epic = roots[0]['number']
            if roots[0].get('title') != spec['title']:
                self.warnings.append(f'epic #{self.plan.epic} title differs from the plan; not edited')

    def create_epic(self) -> None:
        spec = self.plan.epic_spec
        if not spec:
            return
        if self.plan.epic and not self.epic_created:
            self._act('reuse', 'epic', f'#{self.plan.epic} {spec["title"]}', True)
            return
        body = render_epic_body(self.plan)
        if not self.execute:
            self._act('epic', 'epic', f'create epic "{spec["title"]}"', False)
            return
        created = self._write('POST', f'{self.base}/issues',
                              {'title': spec['title'], 'body': body, 'labels': [self.plan.label]})
        self.plan.epic, self.epic_created = created['number'], True
        self._act('epic', 'epic', f'#{created["number"]} {spec["title"]}', True)

    def find_tasks(self, subs: list[dict], labelled: list[dict]) -> None:
        if not self.plan.epic:
            return                      # a new epic has no tasks yet
        found: dict[str, list[dict]] = {}
        seen: set[int] = set()
        for issue in subs + labelled:
            if issue['id'] in seen or 'pull_request' in issue:
                continue
            seen.add(issue['id'])
            meta = parse_marker(issue.get('body'))
            if meta and meta.get('epic') == self.plan.epic_ref:
                found.setdefault(meta['key'], []).append(issue)
        dupes = {k: v for k, v in found.items() if len(v) > 1}
        if dupes:
            raise PlanError([f'task {k} already exists as several issues: '
                             + ', '.join(f'#{i["number"]}' for i in v)
                             + '; closing extras does not resolve marker identity. With explicit authorization, '
                             'choose the canonical task and rename only the extras\' workforce-epic '
                             'markers to workforce-epic-superseded; preserve their content. '
                             'See references/github.md, Duplicate-marker recovery, then dry-run again'
                             for k, v in dupes.items()])
        keys = set(self.plan.by_key)
        for k, (issue,) in found.items():
            if k in keys:
                self.issues[k] = {f: issue.get(f) for f in ('number', 'id', 'title', 'state', 'body')}
            else:
                self.warnings.append(f'#{issue["number"]} has marker task {k}, which is not in this plan; left alone')
        for k, i in self.issues.items():
            if i['title'] != self.plan.by_key[k]['title']:
                self.warnings.append(f'task {k} (#{i["number"]}) title differs from the plan; not edited')
            if i['state'] != 'open':
                self.warnings.append(f'task {k} (#{i["number"]}) is already closed')

    def check_scope_drift(self) -> None:
        candidates = []
        aliases = {key: key for key in self.plan.by_key}
        aliases.update({f'{key} (new)': key for key in self.plan.by_key})
        aliases.update({f'#{issue["number"]}': key for key, issue in self.issues.items()})
        if self.existing_epic and self.plan.epic_spec:
            candidates.append(('epic', self.existing_epic, self.plan.epic_spec['title'],
                               render_epic_body(self.plan), True))
        for key, issue in self.issues.items():
            task = self.plan.by_key[key]
            refs = {b: self._ref(b) for b in task['blocked_by']}
            candidates.append((key, issue, task['title'], render_body(self.plan, task, refs), False))
        for key, issue, title, proposed, root in candidates:
            changes = body_drift(issue.get('body') or '', proposed, root=root,
                                 dependency_aliases=aliases)
            if issue['title'] != title:
                changes['Title'] = {'current': issue['title'], 'proposed': title}
            if changes:
                self.drift.append({'task': key, 'issue': issue['number'], 'sections': changes})
        if self.drift:
            errors = []
            for item in self.drift:
                label = f'{item["task"]} (#{item["issue"]})'
                errors.append(f'scope drift in {label}: ' + ', '.join(item['sections']))
                for section, values in item['sections'].items():
                    diff = '\n'.join(difflib.unified_diff(values['current'].splitlines(),
                                     values['proposed'].splitlines(),
                                     fromfile=f'{label} current {section}',
                                     tofile=f'{label} proposed {section}', lineterm=''))
                    self.log(diff)
            errors.append('No writes were made. Retain existing scope by aligning the local plan, '
                          'or make separately authorized manual issue edits preserving markers and human text. '
                          'Then validate and dry-run again; apply never edits existing bodies or titles.')
            raise PlanError(errors)

    def check_external_blockers(self) -> None:
        for t in self.plan.tasks:
            for b in t['blocked_by']:
                m = EXTERNAL_RE.match(b)
                if m and b not in self.external:
                    try:
                        ext = self.gh.rest('GET', f'{self.base}/issues/{m.group(1)}')
                    except GhError as e:
                        if e.status == 404:
                            raise PlanError([f'task {t["key"]}: blocker {b} does not exist in {self.plan.repo}'])
                        raise
                    if 'pull_request' in ext:
                        raise PlanError([f'task {t["key"]}: blocker {b} is a pull request, not an issue'])
                    self.external[b] = {'number': ext['number'], 'id': ext['id']}

    def ensure_label(self) -> None:
        try:
            self.gh.rest('GET', f'{self.base}/labels/{quote(self.plan.label, safe="")}')
            return
        except GhError as e:
            if e.status != 404:
                raise
        if self.execute:
            self._write('POST', f'{self.base}/labels',
                        {'name': self.plan.label, 'color': LABEL_COLOR, 'description': LABEL_DESC})
        self._act('label', None, f'create label "{self.plan.label}"', self.execute)

    def _ref(self, blocker: str) -> str:
        if blocker in self.external:
            return f'#{self.external[blocker]["number"]}'
        if blocker in self.issues:
            return f'#{self.issues[blocker]["number"]}'
        return f'{blocker} (new)'

    def _blocker_id(self, blocker: str) -> int | None:
        src = self.external.get(blocker) or self.issues.get(blocker)
        return src['id'] if src else None

    def tasks(self) -> None:
        for key in self.plan.order:
            task = self.plan.by_key[key]
            issue = self.issues.get(key)
            existed = issue is not None
            if existed:
                self._act('reuse', key, f'#{issue["number"]} {task["title"]}', True)
            else:
                refs = {b: self._ref(b) for b in task['blocked_by']}
                body = render_body(self.plan, task, refs)
                if self.execute:
                    created = self._write('POST', f'{self.base}/issues',
                                          {'title': task['title'], 'body': body, 'labels': [self.plan.label]})
                    issue = self.issues[key] = {'number': created['number'], 'id': created['id'],
                                                'title': created['title'], 'state': 'open'}
                    self._act('create', key, f'#{issue["number"]} {task["title"]}', True)
                else:
                    self._act('create', key, task['title'], False)

            if issue is None or issue['id'] not in self.sub_ids:
                self.link(key, issue)
            self.dependencies(key, task, issue, existed)

    def link(self, key: str, issue: dict | None) -> None:
        label = f'#{issue["number"]}' if issue else key
        if not self.execute:
            self._act('sub-issue', key, f'link {label} under {self.plan.epic_label}', False)
            return
        try:
            self._write('POST', f'{self.base}/issues/{self.plan.epic}/sub_issues', {'sub_issue_id': issue['id']})
        except GhError as e:
            if e.status != 422:
                raise
            parent = None
            try:
                parent = self.gh.rest('GET', f'{self.base}/issues/{issue["number"]}/parent')
            except GhError:
                pass
            if parent and parent.get('number') != self.plan.epic:
                raise PlanError([f'task {key} (#{issue["number"]}) is already a sub-issue of '
                                 f'#{parent["number"]}; not moving it. Detach it or drop it from the plan'])
            if not parent:
                raise e
        self.sub_ids.add(issue['id'])
        self._act('sub-issue', key, f'linked {label} under epic #{self.plan.epic}', True)

    def dependencies(self, key: str, task: dict, issue: dict | None, existed: bool) -> None:
        if not task['blocked_by']:
            return
        have: set[int] = set()
        if existed and self.deps_supported:
            try:
                have = {i['id'] for i in self.gh.paginate(
                    f'{self.base}/issues/{issue["number"]}/dependencies/blocked_by')}
            except GhError as e:
                if e.status not in (404, 410):
                    raise
                self._deps_unavailable(e)
        for b in task['blocked_by']:
            bid = self._blocker_id(b)
            label = self._ref(b)
            if bid is not None and bid in have:
                continue
            target = f'#{issue["number"]}' if issue else key
            if not self.execute or not self.deps_supported:
                if self.deps_supported:
                    self._act('blocked-by', key, f'{target} blocked by {label}', False)
                continue
            try:
                self._write('POST', f'{self.base}/issues/{issue["number"]}/dependencies/blocked_by',
                            {'issue_id': bid})
                self._act('blocked-by', key, f'{target} blocked by {label}', True)
            except GhError as e:
                if e.status not in (404, 410):
                    raise
                self._deps_unavailable(e)

    def _deps_unavailable(self, e: GhError) -> None:
        if self.deps_supported:
            self.deps_supported = False
            self.warnings.append(f'issue dependencies API unavailable ({e}); '
                                 'blockers are listed only in each issue body')

    def run(self) -> None:
        self.preflight()
        self.ensure_label()
        self.create_epic()
        self.tasks()

    def report(self) -> dict:
        return {
            'repo': self.plan.repo, 'epic': self.plan.epic, 'epic_created': self.epic_created,
            'executed': self.execute,
            'tasks': {k: self.issues[k]['number'] for k in self.plan.order if k in self.issues},
            'actions': self.actions, 'warnings': self.warnings,
            'scope_reconciled': not self.drift, 'drift': self.drift,
        }


def main(argv: list[str] | None = None, gh: Gh | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    for name in ('validate', 'render', 'apply'):
        p = sub.add_parser(name)
        p.add_argument('plan')
        p.add_argument('--json', action='store_true', help='machine-readable output')
        p.add_argument('--max-tasks', type=int, default=50)
        if name == 'render':
            p.add_argument('--task', help='render only this task key')
        if name == 'apply':
            p.add_argument('--execute', action='store_true', help='perform writes (default is a dry run)')
            p.add_argument('--delay', type=float, default=1.0, help='seconds between writes')
    args = ap.parse_args(argv)

    try:
        plan = load_plan(args.plan, args.max_tasks)
    except PlanError as e:
        print('plan invalid:\n  ' + '\n  '.join(e.errors), file=sys.stderr)
        return 2

    if args.cmd == 'validate':
        if args.json:
            print(json.dumps({'ok': True, 'order': plan.order, 'warnings': plan.warnings}, indent=2))
        else:
            print(f'plan ok: {len(plan.tasks)} tasks for {plan.repo} {plan.epic_label}; '
                  f'order {" -> ".join(plan.order)}')
            for w in plan.warnings:
                print(f'warning: {w}')
        return 0

    if args.cmd == 'render':
        keys = [args.task] if args.task else plan.order
        if args.task and args.task not in plan.by_key:
            print(f'unknown task {args.task}', file=sys.stderr)
            return 2
        out = {}
        if plan.epic_spec and not args.task:
            out['epic'] = {'title': plan.epic_spec['title'], 'body': render_epic_body(plan)}
        for k in keys:
            t = plan.by_key[k]
            out[k] = {'title': t['title'],
                      'body': render_body(plan, t, {b: b for b in t['blocked_by']})}
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            for k, v in out.items():
                print(f'===== {k}: {v["title"]}\n{v["body"]}')
        return 0

    log = (lambda *_: None) if args.json else print
    applier = Applier(plan, gh or Gh(), execute=args.execute, delay=args.delay, log=log)
    if not args.json:
        print(f'{"APPLY" if args.execute else "DRY RUN"}: {plan.repo} {plan.epic_label} label "{plan.label}"')
    code = 0
    try:
        applier.run()
    except PlanError as e:
        print('stopped:\n  ' + '\n  '.join(e.errors), file=sys.stderr)
        code = 2
    except GhError as e:
        print(f'stopped on GitHub error: {e}\nRe-run the same command to resume; '
              'completed steps are detected and skipped.', file=sys.stderr)
        code = 1
    report = applier.report()
    report['ok'] = code == 0
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for w in report['warnings']:
            print(f'warning: {w}')
        if code == 0 and not args.execute:
            print('dry run only: nothing was written. Re-run with --execute after approval.')
    return code


if __name__ == '__main__':
    sys.exit(main())
