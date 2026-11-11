"""Shared helpers for create-workforce-epic: plan validation, issue rendering,
task markers, and a thin `gh api` client. Standard library only."""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable

PLAN_VERSION = 1
DEFAULT_LABEL = 'workforce'
MAX_TASKS = 50          # hard cap per plan; GitHub also caps sub-issues per parent
SOFT_MAX_TASKS = 15     # above this, suggest splitting the epic
MAX_BODY = 65000        # GitHub rejects issue bodies over 65536 characters
MARKER_RE = re.compile(r'<!--\s*workforce-epic:\s*(\{.*?\})\s*-->', re.S)
EPIC_MARKER_RE = re.compile(r'<!--\s*workforce-epic-root:\s*(\{.*?\})\s*-->', re.S)
KEY_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,31}$')
REPO_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$')
EXTERNAL_RE = re.compile(r'^#([1-9][0-9]*)$')
KINDS = ('agent', 'human')
TIERS = ('easy', 'hard')


class PlanError(Exception):
    """The plan is invalid; `errors` lists every problem found."""

    def __init__(self, errors: list[str]):
        super().__init__('\n'.join(errors))
        self.errors = errors


@dataclass
class Plan:
    repo: str
    epic: int | None                      # None until a new epic is found or created
    label: str
    tasks: list[dict]
    criteria: list[dict]
    order: list[str]                      # task keys, dependencies first
    warnings: list[str] = field(default_factory=list)
    epic_spec: dict | None = None         # set when the plan creates its own epic

    @property
    def by_key(self) -> dict[str, dict]:
        return {t['key']: t for t in self.tasks}

    @property
    def epic_ref(self) -> str:
        return f'{self.repo}#{self.epic if self.epic else "new"}'

    @property
    def epic_label(self) -> str:
        if self.epic:
            return f'#{self.epic}'
        return f'new epic "{self.epic_spec["title"]}"'


# ---------------------------------------------------------------- validation

def _str_list(task: dict, name: str, errs: list[str], where: str) -> list[str]:
    value = task.get(name, [])
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        errs.append(f'{where}: "{name}" must be a list of non-empty strings')
        return []
    return value


def _path_prefix(path: str) -> str:
    cut = len(path)
    for ch in '*?[':
        i = path.find(ch)
        if i != -1:
            cut = min(cut, i)
    return path[:cut].rstrip('/')


def paths_overlap(a: str, b: str) -> bool:
    pa, pb = _path_prefix(a), _path_prefix(b)
    if not pa or not pb:
        return True          # a bare glob or repo root overlaps everything
    return pa == pb or pa.startswith(pb + '/') or pb.startswith(pa + '/')


def _topo_order(keys: list[str], deps: dict[str, list[str]]) -> tuple[list[str], list[str]]:
    """Kahn's algorithm, stable by declaration order. Returns (order, keys in cycles)."""
    indeg = {k: 0 for k in keys}
    users: dict[str, list[str]] = {k: [] for k in keys}
    for k in keys:
        for d in deps[k]:
            indeg[k] += 1
            users[d].append(k)
    ready = [k for k in keys if indeg[k] == 0]
    order: list[str] = []
    while ready:
        k = ready.pop(0)
        order.append(k)
        for u in users[k]:
            indeg[u] -= 1
            if indeg[u] == 0:
                ready.append(u)
        ready.sort(key=keys.index)
    return order, [k for k in keys if k not in order]


def _ancestors(order: list[str], deps: dict[str, list[str]]) -> dict[str, set[str]]:
    anc: dict[str, set[str]] = {}
    for k in order:
        s: set[str] = set()
        for d in deps[k]:
            s.add(d)
            s |= anc[d]
        anc[k] = s
    return anc


def validate_plan(data: Any, max_tasks: int = MAX_TASKS) -> Plan:
    errs: list[str] = []
    warns: list[str] = []
    if not isinstance(data, dict):
        raise PlanError(['plan must be a JSON object'])
    if data.get('version') != PLAN_VERSION:
        errs.append(f'"version" must be {PLAN_VERSION}')
    repo = data.get('repo')
    if not isinstance(repo, str) or not REPO_RE.match(repo):
        errs.append('"repo" must look like owner/name')
    epic = data.get('epic')
    epic_spec = None
    if isinstance(epic, dict):
        epic_spec, epic = _validate_epic_spec(epic, errs), None
    elif not isinstance(epic, int) or isinstance(epic, bool) or epic < 1:
        errs.append('"epic" must be an existing issue number or an object describing a new epic')
    label = data.get('label', DEFAULT_LABEL)
    if not isinstance(label, str) or not label.strip() or len(label) > 50 or ',' in label:
        errs.append('"label" must be a non-empty string of at most 50 characters without commas')

    tasks = data.get('tasks')
    if not isinstance(tasks, list) or not tasks:
        errs.append('"tasks" must be a non-empty list')
        tasks = []
    if len(tasks) > max_tasks:
        errs.append(f'{len(tasks)} tasks exceeds the limit of {max_tasks}; split the epic or apply in batches')
    elif len(tasks) > SOFT_MAX_TASKS:
        warns.append(f'{len(tasks)} tasks is a lot for one epic; consider splitting it into phases')

    keys: list[str] = []
    deps: dict[str, list[str]] = {}
    for i, t in enumerate(tasks):
        where = f'task[{i}]'
        if not isinstance(t, dict):
            errs.append(f'{where}: must be an object')
            continue
        key = t.get('key')
        if not isinstance(key, str) or not KEY_RE.match(key):
            errs.append(f'{where}: "key" must match {KEY_RE.pattern}')
            continue
        where = f'task {key}'
        if key in keys:
            errs.append(f'{where}: duplicate key')
            continue
        keys.append(key)
        title = t.get('title')
        if not isinstance(title, str) or not title.strip() or len(title) > 256:
            errs.append(f'{where}: "title" must be 1-256 characters')
        kind = t.setdefault('kind', 'agent')
        if kind not in KINDS:
            errs.append(f'{where}: "kind" must be one of {", ".join(KINDS)}')
        tier = t.get('tier')
        if kind == 'agent' and tier not in TIERS:
            errs.append(f'{where}: agent tasks need "tier" of easy or hard')
        if kind == 'human' and tier is not None:
            errs.append(f'{where}: human tasks must not set "tier"')
        summary = t.get('summary')
        if not isinstance(summary, str) or not summary.strip():
            errs.append(f'{where}: "summary" is required')
        for name in ('scope', 'out_of_scope', 'owned_paths', 'acceptance', 'verify'):
            t[name] = _str_list(t, name, errs, where)
        if not t['acceptance']:
            errs.append(f'{where}: at least one acceptance criterion is required')
        if kind == 'agent':
            if not t['verify']:
                errs.append(f'{where}: agent tasks need at least one verification command')
            if not t['owned_paths']:
                warns.append(f'{where}: no owned_paths; parallel scheduling cannot check overlap')
        notes = t.get('notes', '')
        if not isinstance(notes, str):
            errs.append(f'{where}: "notes" must be a string')
        blocked = t.get('blocked_by', [])
        if not isinstance(blocked, list) or not all(isinstance(b, str) for b in blocked):
            errs.append(f'{where}: "blocked_by" must be a list of task keys or "#<number>" strings')
            blocked = []
        if len(set(blocked)) != len(blocked):
            errs.append(f'{where}: "blocked_by" has duplicates')
        t['blocked_by'] = blocked
        deps[key] = []
        for text in _all_text(t):
            if 'workforce-epic' in text:
                errs.append(f'{where}: text must not contain the reserved marker "workforce-epic"')
                break

    for k in keys:
        for b in by_key_list(tasks, k)['blocked_by']:
            m = EXTERNAL_RE.match(b)
            if m:
                if isinstance(epic, int) and int(m.group(1)) == epic:
                    errs.append(f'task {k}: cannot be blocked by its own epic #{epic}')
            elif b == k:
                errs.append(f'task {k}: cannot be blocked by itself')
            elif b in deps:
                deps[k].append(b)
            else:
                errs.append(f'task {k}: unknown blocker "{b}" (use a task key or "#<number>")')

    order, cyclic = _topo_order(keys, deps)
    if cyclic:
        errs.append('dependency cycle among tasks: ' + ', '.join(cyclic))

    criteria = data.get('criteria', [])
    covered: set[str] = set()
    if not isinstance(criteria, list) or not criteria:
        errs.append('"criteria" must list the epic\'s acceptance criteria (each covered or deferred)')
        criteria = []
    seen_ids: set[str] = set()
    for i, c in enumerate(criteria):
        where = f'criteria[{i}]'
        if not isinstance(c, dict):
            errs.append(f'{where}: must be an object')
            continue
        cid = c.get('id')
        if not isinstance(cid, str) or not KEY_RE.match(cid):
            errs.append(f'{where}: "id" must match {KEY_RE.pattern}')
            continue
        where = f'criterion {cid}'
        if cid in seen_ids:
            errs.append(f'{where}: duplicate id')
        seen_ids.add(cid)
        if not isinstance(c.get('text'), str) or not c['text'].strip():
            errs.append(f'{where}: "text" is required')
        cov, deferred = c.get('covered_by'), c.get('deferred')
        if bool(cov) == bool(deferred):
            errs.append(f'{where}: set exactly one of "covered_by" (task keys) or "deferred" (reason)')
        if cov:
            if not isinstance(cov, list) or not all(isinstance(x, str) for x in cov):
                errs.append(f'{where}: "covered_by" must be a list of task keys')
            else:
                for x in cov:
                    if x not in deps:
                        errs.append(f'{where}: covered_by unknown task "{x}"')
                    covered.add(x)
        if deferred is not None and (not isinstance(deferred, str) or not deferred.strip()):
            errs.append(f'{where}: "deferred" must be a non-empty reason')

    if not errs:
        for k in keys:
            if k not in covered:
                warns.append(f'task {k}: covers no epic criterion; is it needed?')
        anc = _ancestors(order, deps)
        agents = [t for t in tasks if t['kind'] == 'agent']
        for i, a in enumerate(agents):
            for b in agents[i + 1:]:
                if a['key'] in anc[b['key']] or b['key'] in anc[a['key']]:
                    continue
                hits = [(p, q) for p in a['owned_paths'] for q in b['owned_paths'] if paths_overlap(p, q)]
                if hits:
                    p, q = hits[0]
                    warns.append(f'tasks {a["key"]} and {b["key"]} are unordered but both own '
                                 f'"{p}"/"{q}"; they cannot run in parallel')
    if errs:
        raise PlanError(errs)
    return Plan(repo=repo, epic=epic, label=label.strip(), tasks=tasks,
                criteria=criteria, order=order, warnings=warns, epic_spec=epic_spec)


def _validate_epic_spec(spec: dict, errs: list[str]) -> dict:
    where = 'epic'
    if not isinstance(spec.get('key'), str) or not KEY_RE.match(spec['key']):
        errs.append(f'{where}: "key" must match {KEY_RE.pattern} (unique per repository, stable across re-runs)')
    title = spec.get('title')
    if not isinstance(title, str) or not title.strip() or len(title) > 256:
        errs.append(f'{where}: "title" must be 1-256 characters')
    if not isinstance(spec.get('summary'), str) or not spec['summary'].strip():
        errs.append(f'{where}: "summary" is required')
    for name in ('background', 'notes'):
        if not isinstance(spec.get(name, ''), str):
            errs.append(f'{where}: "{name}" must be a string')
    spec['out_of_scope'] = _str_list(spec, 'out_of_scope', errs, where)
    texts = [spec.get(n) for n in ('title', 'summary', 'background', 'notes')] + spec['out_of_scope']
    if any(isinstance(t, str) and 'workforce-epic' in t for t in texts):
        errs.append(f'{where}: text must not contain the reserved marker "workforce-epic"')
    return spec


def by_key_list(tasks: list[dict], key: str) -> dict:
    return next(t for t in tasks if isinstance(t, dict) and t.get('key') == key)


def _all_text(t: dict) -> list[str]:
    out = [v for v in (t.get('title'), t.get('summary'), t.get('notes')) if isinstance(v, str)]
    for name in ('scope', 'out_of_scope', 'owned_paths', 'acceptance', 'verify'):
        v = t.get(name)
        if isinstance(v, list):
            out += [x for x in v if isinstance(x, str)]
    return out


def load_plan(path: str, max_tasks: int = MAX_TASKS) -> Plan:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except OSError as e:
        raise PlanError([f'cannot read plan: {e}']) from e
    except json.JSONDecodeError as e:
        raise PlanError([f'plan is not valid JSON: {e}']) from e
    return validate_plan(data, max_tasks)


# ---------------------------------------------------------------- markers & rendering

def make_marker(plan: Plan, task: dict) -> str:
    meta = {'v': 1, 'epic': plan.epic_ref, 'key': task['key'], 'kind': task['kind']}
    if task['kind'] == 'agent':
        meta['tier'] = task['tier']
    return f'<!-- workforce-epic: {json.dumps(meta, separators=(",", ":"))} -->'


def make_epic_marker(spec: dict) -> str:
    return f'<!-- workforce-epic-root: {json.dumps({"v": 1, "key": spec["key"]}, separators=(",", ":"))} -->'


def parse_epic_marker(body: str | None) -> dict | None:
    m = EPIC_MARKER_RE.search(body or '')
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    return meta if isinstance(meta, dict) and isinstance(meta.get('key'), str) else None


def render_epic_body(plan: Plan) -> str:
    spec = plan.epic_spec
    parts = [make_epic_marker(spec), '## Summary\n' + spec['summary'].strip()]
    if spec.get('background', '').strip():
        parts.append('## Background\n' + spec['background'].strip())
    crit = []
    for c in plan.criteria:
        if c.get('deferred'):
            crit.append(f'- **{c["id"]}** (deferred): {c["text"]}. {c["deferred"]}')
        else:
            crit.append(f'- [ ] **{c["id"]}**: {c["text"]}')
    parts.append('## Acceptance criteria\n' + '\n'.join(crit))
    if spec['out_of_scope']:
        parts.append('## Out of scope\n' + _bullets(spec['out_of_scope']))
    if spec.get('notes', '').strip():
        parts.append('## Notes\n' + spec['notes'].strip())
    parts.append('## Tasks\nTracked as sub-issues of this epic, with blocked-by dependencies. '
                 'Created by create-workforce-epic.')
    body = '\n\n'.join(parts) + '\n'
    if len(body) > MAX_BODY:
        raise PlanError([f'epic: rendered body is {len(body)} characters, over {MAX_BODY}'])
    return body


def parse_marker(body: str | None) -> dict | None:
    if not body:
        return None
    m = MARKER_RE.search(body)
    if not m:
        return None
    try:
        meta = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(meta, dict) or not isinstance(meta.get('key'), str) or not isinstance(meta.get('epic'), str):
        return None
    return meta


def _bullets(items: list[str], check: bool = False) -> str:
    prefix = '- [ ] ' if check else '- '
    return '\n'.join(prefix + i for i in items)


def render_body(plan: Plan, task: dict, refs: dict[str, str]) -> str:
    """refs maps blocker strings (task keys and "#n") to display text such as "#12"."""
    head = f'> Part of {f"#{plan.epic}" if plan.epic else "the new epic"} · task `{task["key"]}` · '
    head += '**needs a human**' if task['kind'] == 'human' else f'tier **{task["tier"]}**'
    parts = [make_marker(plan, task), head, '## Summary\n' + task['summary'].strip()]
    if task['scope']:
        parts.append('## Scope\n' + _bullets(task['scope']))
    if task['out_of_scope']:
        parts.append('## Out of scope\n' + _bullets(task['out_of_scope']))
    if task['owned_paths']:
        parts.append('## Owned paths\n' + _bullets([f'`{p}`' for p in task['owned_paths']]))
    parts.append('## Acceptance criteria\n' + _bullets(task['acceptance'], check=True))
    if task['verify']:
        parts.append('## Verification\n```bash\n' + '\n'.join(task['verify']) + '\n```')
    covers = [c for c in plan.criteria if task['key'] in (c.get('covered_by') or [])]
    if covers:
        parts.append('## Epic criteria covered\n' + _bullets([f'**{c["id"]}**: {c["text"]}' for c in covers]))
    blockers = [refs.get(b, b) for b in task['blocked_by']]
    parts.append('## Dependencies\n' + ('Blocked by ' + ', '.join(blockers) if blockers else 'None. This task can start first.'))
    if task.get('notes', '').strip():
        parts.append('## Notes\n' + task['notes'].strip())
    body = '\n\n'.join(parts) + '\n'
    if len(body) > MAX_BODY:
        raise PlanError([f'task {task["key"]}: rendered body is {len(body)} characters, over {MAX_BODY}'])
    return body


# ---------------------------------------------------------------- GitHub client

class GhError(Exception):
    def __init__(self, status: int | None, message: str):
        super().__init__(f'HTTP {status}: {message}' if status else message)
        self.status = status
        self.message = message


Runner = Callable[[list[str], str | None], 'subprocess.CompletedProcess[str]']


def _default_runner(args: list[str], stdin: str | None) -> 'subprocess.CompletedProcess[str]':
    return subprocess.run(args, input=stdin, capture_output=True, text=True, timeout=120)


def parse_include(stdout: str) -> tuple[int | None, Any]:
    text = stdout.replace('\r\n', '\n')
    m = re.match(r'HTTP/[\d.]+ (\d{3})', text)
    if not m:
        return None, None
    _, sep, payload = text.partition('\n\n')
    payload = payload.strip()
    if not sep or not payload:
        return int(m.group(1)), None
    try:
        return int(m.group(1)), json.loads(payload)
    except json.JSONDecodeError:
        return int(m.group(1)), payload


class Gh:
    """Minimal `gh api` wrapper. Raises GhError for non-2xx or transport failures."""

    def __init__(self, runner: Runner | None = None):
        self.run = runner or _default_runner

    def rest(self, method: str, path: str, body: dict | None = None) -> Any:
        args = ['gh', 'api', '--method', method, '--include',
                '-H', 'Accept: application/vnd.github+json', path]
        if body is not None:
            args += ['--input', '-']
        try:
            p = self.run(args, json.dumps(body) if body is not None else None)
        except (OSError, subprocess.SubprocessError) as e:
            raise GhError(None, f'gh failed: {e}') from e
        status, data = parse_include(p.stdout)
        if status is None:
            raise GhError(None, (p.stderr or p.stdout or 'no response from gh').strip())
        if status >= 300:
            msg = data.get('message') if isinstance(data, dict) else (data or p.stderr.strip())
            raise GhError(status, str(msg))
        return data

    def paginate(self, path: str, limit: int = 1000) -> list:
        sep = '&' if '?' in path else '?'
        out: list = []
        page = 1
        while True:
            chunk = self.rest('GET', f'{path}{sep}per_page=100&page={page}')
            if not isinstance(chunk, list):
                raise GhError(None, f'expected a list from {path}')
            out += chunk
            if len(chunk) < 100 or len(out) >= limit:
                return out
            page += 1

    def graphql(self, query: str, variables: dict) -> dict:
        try:
            p = self.run(['gh', 'api', 'graphql', '--input', '-'],
                         json.dumps({'query': query, 'variables': variables}))
        except (OSError, subprocess.SubprocessError) as e:
            raise GhError(None, f'gh failed: {e}') from e
        try:
            data = json.loads(p.stdout)
        except json.JSONDecodeError:
            raise GhError(None, (p.stderr or p.stdout or 'no response from gh').strip())
        if data.get('errors'):
            raise GhError(None, '; '.join(e.get('message', '?') for e in data['errors']))
        return data['data']
